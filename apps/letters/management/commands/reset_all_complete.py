# apps\letters\management\commands\reset_all_complete.py
"""
COMPLETE, ONE-TIME reset of ALL letter test data (both FACS and Artiva) for
production launch.

For each of FACSLetters and ArtivaLetters, this wipes:
  - the live records themselves
  - everything generically linked to them: SessionsApproval, RadiusApproval,
    LetterVersion, Ticket, DocumentAttachment, Comment
  - their simple_history change trail (HistoricalFACSLetters / HistoricalArtivaLetters)
  - letters_auditlog entries (apps.letters.models.AuditLog) referencing any of the above
  - accounts_useractivitylog entries (apps.accounts.models.UserActivityLog) referencing any of the above

Use this ONLY for clearing developer/test data before go-live. Do not run
this against a database that has real production history you want to keep.
Nothing outside the letters (FACS + Artiva) domain is touched — users,
departments, documents, roles, etc. are all left alone.

Run manually by a developer from the terminal. Not exposed anywhere in the
app/UI. DESTRUCTIVE and IRREVERSIBLE short of a DB backup restore.

Usage (from project root, with venv active):

    Preview counts without deleting anything:
        python manage.py reset_all_complete --dry-run

    Actually delete (asks for typed confirmation):
        python manage.py reset_all_complete

    Actually delete without the interactive prompt:
        python manage.py reset_all_complete --yes

    Reset only one system instead of both:
        python manage.py reset_all_complete --only facs
        python manage.py reset_all_complete --only artiva
"""
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.letters.models import (
    FACSLetters,
    ArtivaLetters,
    SessionsApproval,
    RadiusApproval,
    LetterVersion,
    Ticket,
    DocumentAttachment,
    Comment,
    AuditLog,
)
from apps.accounts.models import UserActivityLog

CONFIRM_PHRASE = 'DELETE ALL LETTER DATA'

# Related models that hang off a letter row via generic (content_type + object_id) FK
RELATED_MODELS = [
    ('SessionsApproval', SessionsApproval),
    ('RadiusApproval', RadiusApproval),
    ('LetterVersion', LetterVersion),
    ('Ticket', Ticket),
    ('DocumentAttachment', DocumentAttachment),
    ('Comment', Comment),
]

SYSTEMS = {
    'facs': ('FACSLetters', FACSLetters),
    'artiva': ('ArtivaLetters', ArtivaLetters),
}


class Command(BaseCommand):
    help = ('COMPLETE one-time reset of ALL letter data (FACS and/or Artiva), '
            'including audit trail and history. Developer use only.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                             help='Show what would be deleted without deleting anything')
        parser.add_argument('--yes', action='store_true',
                             help='Skip the interactive confirmation prompt')
        parser.add_argument('--only', choices=['facs', 'artiva'], default=None,
                             help='Reset only FACS or only Artiva instead of both')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_confirm = options['yes']
        only = options['only']

        targets = [SYSTEMS[only]] if only else list(SYSTEMS.values())

        plan = []
        for model_name, model in targets:
            plan.append(self._build_plan(model_name, model))

        if all(p['letter_ids'] == [] for p in plan):
            self.stdout.write('No matching letter records exist. Nothing to reset.')
            return

        self._report(plan)

        if dry_run:
            self.stdout.write(self.style.WARNING('\n--dry-run: nothing was deleted.'))
            return

        if not skip_confirm:
            systems_label = ' + '.join(p['model_name'] for p in plan)
            self.stdout.write(self.style.WARNING(
                f'\nThis permanently erases ALL {systems_label} data AND its audit trail/history. '
                f'This cannot be undone. Type "{CONFIRM_PHRASE}" (without quotes) to proceed:'
            ))
            typed = input('> ').strip()
            if typed != CONFIRM_PHRASE:
                self.stdout.write(self.style.ERROR('Confirmation phrase did not match. Aborted, nothing deleted.'))
                return

        with transaction.atomic():
            for p in plan:
                self._execute(p)

    # ------------------------------------------------------------------ #

    def _build_plan(self, model_name, model):
        """Gather every id that needs deleting for this letter system, without deleting anything yet."""
        ct = ContentType.objects.get_for_model(model)
        letter_ids = list(model.objects.values_list('id', flat=True))

        related_ids = {}
        for name, related_model in RELATED_MODELS:
            related_ids[name] = list(
                related_model.objects.filter(content_type=ct, object_id__in=letter_ids).values_list('id', flat=True)
            ) if letter_ids else []

        historical_model = model.history.model
        historical_count = historical_model.objects.filter(id__in=letter_ids).count() if letter_ids else 0

        auditlog_counts = {}
        auditlog_counts[model_name] = AuditLog.objects.filter(
            content_type=ct, object_id__in=letter_ids
        ).count() if letter_ids else 0
        for name, related_model in RELATED_MODELS:
            ids = related_ids[name]
            if ids:
                rct = ContentType.objects.get_for_model(related_model)
                auditlog_counts[name] = AuditLog.objects.filter(content_type=rct, object_id__in=ids).count()
            else:
                auditlog_counts[name] = 0

        activitylog_counts = {}
        activitylog_counts[model_name] = UserActivityLog.objects.filter(
            model_name=model_name, object_id__in=[str(i) for i in letter_ids]
        ).count() if letter_ids else 0
        for name, _ in RELATED_MODELS:
            ids = related_ids[name]
            activitylog_counts[name] = UserActivityLog.objects.filter(
                model_name=name, object_id__in=[str(i) for i in ids]
            ).count() if ids else 0

        return {
            'model_name': model_name,
            'model': model,
            'content_type': ct,
            'letter_ids': letter_ids,
            'related_ids': related_ids,
            'historical_model': historical_model,
            'historical_count': historical_count,
            'auditlog_counts': auditlog_counts,
            'activitylog_counts': activitylog_counts,
        }

    def _report(self, plan):
        self.stdout.write('The following would be PERMANENTLY deleted:\n')
        for p in plan:
            self.stdout.write(f"=== {p['model_name']} ===")
            self.stdout.write(f"  {p['model_name']} (live records): {len(p['letter_ids'])}")
            for name, _ in RELATED_MODELS:
                self.stdout.write(f"  {name} (live records): {len(p['related_ids'][name])}")
            self.stdout.write(f"  Historical{p['model_name']} (change trail): {p['historical_count']}")
            self.stdout.write('  letters_auditlog entries:')
            for name, count in p['auditlog_counts'].items():
                self.stdout.write(f'    {name}: {count}')
            self.stdout.write('  accounts_useractivitylog entries:')
            for name, count in p['activitylog_counts'].items():
                self.stdout.write(f'    {name}: {count}')
            self.stdout.write('')

    def _execute(self, p):
        model_name = p['model_name']
        model = p['model']
        ct = p['content_type']
        letter_ids = p['letter_ids']
        related_ids = p['related_ids']

        if not letter_ids:
            self.stdout.write(f'{model_name}: nothing to delete.')
            return

        deleted_auditlog = 0
        n, _ = AuditLog.objects.filter(content_type=ct, object_id__in=letter_ids).delete()
        deleted_auditlog += n
        for name, related_model in RELATED_MODELS:
            ids = related_ids[name]
            if ids:
                rct = ContentType.objects.get_for_model(related_model)
                n, _ = AuditLog.objects.filter(content_type=rct, object_id__in=ids).delete()
                deleted_auditlog += n

        deleted_activitylog = 0
        n, _ = UserActivityLog.objects.filter(
            model_name=model_name, object_id__in=[str(i) for i in letter_ids]
        ).delete()
        deleted_activitylog += n
        for name, _ in RELATED_MODELS:
            ids = related_ids[name]
            if ids:
                n, _ = UserActivityLog.objects.filter(
                    model_name=name, object_id__in=[str(i) for i in ids]
                ).delete()
                deleted_activitylog += n

        deleted_historical, _ = p['historical_model'].objects.filter(id__in=letter_ids).delete()

        deleted_related = 0
        for name, related_model in RELATED_MODELS:
            n, _ = related_model.objects.filter(content_type=ct, object_id__in=letter_ids).delete()
            deleted_related += n

        deleted_letters, _ = model.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'{model_name}: deleted {deleted_letters} letters, {deleted_related} related records, '
            f'{deleted_historical} historical rows, {deleted_auditlog} audit log rows, '
            f'{deleted_activitylog} activity log rows.'
        ))