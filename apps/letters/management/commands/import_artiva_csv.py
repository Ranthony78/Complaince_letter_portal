# apps\letters\management\commands\import_artiva_csv.py
"""
ONE-TIME bulk import for Artiva Letters.
Run manually by a developer from the terminal. Not exposed anywhere in the app/UI.

Usage (from project root, with venv active):

    python manage.py import_artiva_csv path\to\artiva_bulk_import_template.csv --user gstevens

Add --reset to wipe all existing ArtivaLetters (and their related approvals,
versions, tickets, documents, comments) before importing:

    python manage.py import_artiva_csv path\to\file.csv --user gstevens --reset

Add --dry-run to validate the CSV and print what WOULD happen without
writing anything to the database:

    python manage.py import_artiva_csv path\to\file.csv --user gstevens --dry-run

Add --no-sessions to skip creating the SessionsApproval record per letter:

    python manage.py import_artiva_csv path\to\file.csv --user gstevens --no-sessions

By default, every letter also gets a RadiusApproval record (Approved), using
the same username as --user for 'CCO or Representative'. To use a different
person for that (e.g. Robert Anthony), pass --radius-approver with their
actual username:

    python manage.py import_artiva_csv path\to\file.csv --user gstevens --radius-approver Ranthony

Add --no-radius to skip creating the RadiusApproval record per letter:

    python manage.py import_artiva_csv path\to\file.csv --user gstevens --no-radius

By default, every letter also gets a LetterVersion (V.0) record so Version
History isn't empty, authored by the --radius-approver (or --user if
--radius-approver wasn't given). Add --no-version to skip this:

    python manage.py import_artiva_csv path\to\file.csv --user gstevens --no-version

Every imported letter is set to status='Completed' (see STATUS_VALUE below).
Comments on the letter, Sessions Approval, and Radius Approval are all set to
IMPORT_COMMENT ("Updated through System Bulk Upload") since there's no
dedicated user field to attribute the bulk import to.
"""
import csv
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.letters.models import (
    ArtivaLetters,
    SessionsApproval,
    RadiusApproval,
    LetterVersion,
    Ticket,
    DocumentAttachment,
    Comment,
)

User = get_user_model()

# ---- Fixed values applied to every imported row (per your instructions) ----
CREATION_TYPE = 'Creation'
COMMUNICATION_TYPE = 'Email'
CREATION_REVISION_DATE = datetime(2026, 4, 15, 0, 0, 0)   # 4/15/2026
PRODUCTION_DATE = datetime(2026, 4, 15).date()             # 4/15/2026
SESSIONS_APPROVAL_DATE = datetime(2026, 5, 29, 0, 0, 0)    # 5/29/2026
RADIUS_APPROVAL_DATE = datetime(2026, 5, 29, 0, 0, 0)      # same date as Sessions unless told otherwise
STATUS_VALUE = 'Completed'                                  # per your instruction
COMPLETED_AT = datetime(2026, 5, 29, 0, 0, 0)               # BaseLetter.save() would normally set this on transition to Completed; bulk_create bypasses save(), so we set it explicitly
IMPORT_COMMENT = 'Updated through System Bulk Upload'        # noted on approvals/letter/version since there's no user field to attribute them to
VERSION_NUMBER = 'V.0'                                       # matches ArtivaLetters.current_version default
VERSION_NOTE = 'Final approved version'
VERSION_REVISION_REASON = 'Final approval'

# ---- Defaults used ONLY when a CSV cell is left blank ----
DEFAULT_SOURCE = 'Internal'
DEFAULT_PRIORITY = 'Medium'
DEFAULT_COMMUNICATION_SUBTYPE = 'Email'

REQUIRED_COLUMNS = ['letter_code', 'timing', 'regulatory']
VALID_TIMING = {'Initial', 'Subsequent', 'Seasonal'}
VALID_REGULATORY = {'Yes', 'No'}


def make_aware(dt):
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


class Command(BaseCommand):
    help = 'One-time bulk import of Artiva Letters from a CSV file (developer use only).'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file')
        parser.add_argument('--user', type=str, required=True,
                             help='Username to set as created_by for every imported letter')
        parser.add_argument('--reset', action='store_true',
                             help='Delete ALL existing ArtivaLetters (and related records) before importing')
        parser.add_argument('--dry-run', action='store_true',
                             help='Validate the CSV and report what would happen, without writing to the DB')
        parser.add_argument('--no-sessions', action='store_true',
                             help='Skip creating a SessionsApproval record for each imported letter')
        parser.add_argument('--radius-approver', type=str, default=None,
                             help="Username to set as 'CCO or Representative' on the RadiusApproval record "
                                  "(e.g. Robert Anthony's username). Defaults to the --user value if not given.")
        parser.add_argument('--no-radius', action='store_true',
                             help='Skip creating a RadiusApproval record for each imported letter')
        parser.add_argument('--no-version', action='store_true',
                             help='Skip creating a LetterVersion (V.0) record for each imported letter')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        username = options['user']
        do_reset = options['reset']
        dry_run = options['dry_run']
        create_sessions = not options['no_sessions']
        create_radius = not options['no_radius']
        create_version = not options['no_version']
        radius_approver_username = options['radius_approver'] or username

        try:
            created_by = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(
                f"No user found with username '{username}'. "
                f"Check the exact username in accounts_user and pass it via --user."
            )

        radius_approver = None
        if create_radius:
            try:
                radius_approver = User.objects.get(username=radius_approver_username)
            except User.DoesNotExist:
                raise CommandError(
                    f"No user found with username '{radius_approver_username}'. "
                    f"Check the exact username in accounts_user and pass it via --radius-approver "
                    f"(e.g. --radius-approver Ranthony for Robert Anthony)."
                )

        rows = self._read_and_validate_csv(csv_path)
        self.stdout.write(self.style.SUCCESS(f'Read {len(rows)} valid row(s) from {csv_path}'))

        if dry_run:
            self.stdout.write(self.style.WARNING('--dry-run: no changes will be made.'))
            self.stdout.write(f'  Would reset existing ArtivaLetters: {do_reset}')
            self.stdout.write(f'  Would create_by user: {created_by.username} (id={created_by.id})')
            self.stdout.write(f'  Status would be set to: {STATUS_VALUE}')
            self.stdout.write(f'  Would create SessionsApproval per letter (Approved, {SESSIONS_APPROVAL_DATE.date()}): {create_sessions}')
            if create_radius:
                self.stdout.write(f'  Would create RadiusApproval per letter (Approved, {RADIUS_APPROVAL_DATE.date()}, '
                                   f'CCO/Rep = {radius_approver.username}): True')
            else:
                self.stdout.write('  Would create RadiusApproval per letter: False')
            self.stdout.write(f'  Would create LetterVersion {VERSION_NUMBER} per letter: {create_version}')
            self.stdout.write(f'  Comments/Final Comments text: "{IMPORT_COMMENT}"')
            for r in rows[:5]:
                self.stdout.write(f'    sample -> {r}')
            if len(rows) > 5:
                self.stdout.write(f'    ... and {len(rows) - 5} more')
            return

        with transaction.atomic():
            if do_reset:
                self._reset_artiva_data()

            created_codes = self._bulk_create(rows, created_by)

            # Fix creation_revision_date and completed_at (auto_now_add / the
            # custom save() logic that would normally set completed_at are both
            # bypassed by bulk_create, so we correct them afterwards with a
            # plain UPDATE).
            ArtivaLetters.objects.filter(letter_code__in=created_codes).update(
                creation_revision_date=make_aware(CREATION_REVISION_DATE),
                completed_at=make_aware(COMPLETED_AT),
            )

            if create_sessions:
                self._create_sessions_approvals(created_codes)

            if create_radius:
                self._create_radius_approvals(created_codes, radius_approver)

            if create_version:
                version_author = radius_approver if radius_approver else created_by
                self._create_letter_versions(created_codes, version_author)

        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {len(created_codes)} ArtivaLetters record(s), status={STATUS_VALUE}.'
        ))

    # ------------------------------------------------------------------ #

    def _read_and_validate_csv(self, csv_path):
        try:
            f = open(csv_path, newline='', encoding='utf-8-sig')
        except OSError as e:
            raise CommandError(f'Could not open CSV file: {e}')

        with f:
            reader = csv.DictReader(f)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise CommandError(f'CSV is missing required column(s): {missing}')

            rows = []
            seen_codes = set()
            errors = []
            for i, raw in enumerate(reader, start=2):  # row 1 is header
                letter_code = (raw.get('letter_code') or '').strip()
                timing = (raw.get('timing') or '').strip()
                regulatory = (raw.get('regulatory') or '').strip()

                if not letter_code:
                    errors.append(f'Row {i}: missing letter_code')
                    continue
                if letter_code in seen_codes:
                    errors.append(f'Row {i}: duplicate letter_code "{letter_code}" within CSV')
                    continue
                if timing and timing not in VALID_TIMING:
                    errors.append(f'Row {i}: invalid timing "{timing}" (must be one of {VALID_TIMING})')
                    continue
                if regulatory and regulatory not in VALID_REGULATORY:
                    errors.append(f'Row {i}: invalid regulatory "{regulatory}" (must be Yes or No)')
                    continue
                if ArtivaLetters.objects.filter(letter_code=letter_code).exists():
                    errors.append(f'Row {i}: letter_code "{letter_code}" already exists in the database')
                    continue

                seen_codes.add(letter_code)
                rows.append({
                    'letter_code': letter_code,
                    'timing': timing,
                    'regulatory': regulatory,
                    'communication_code': (raw.get('communication_code') or '').strip() or letter_code,
                    'source': (raw.get('source') or '').strip() or DEFAULT_SOURCE,
                    'priority': (raw.get('priority') or '').strip() or DEFAULT_PRIORITY,
                    'communication_subtype': (raw.get('communication_subtype') or '').strip() or DEFAULT_COMMUNICATION_SUBTYPE,
                    'document_description': (raw.get('document_description') or '').strip() or f'Document for {letter_code}',
                    'letter_description': (raw.get('letter_description') or '').strip() or f'Bulk imported letter {letter_code}',
                })

            if errors:
                self.stdout.write(self.style.ERROR(f'{len(errors)} row(s) failed validation and will be SKIPPED:'))
                for e in errors:
                    self.stdout.write(self.style.ERROR(f'  - {e}'))

            if not rows:
                raise CommandError('No valid rows to import after validation. Fix the CSV and try again.')

            return rows

    def _reset_artiva_data(self):
        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)
        artiva_ids = list(ArtivaLetters.objects.values_list('id', flat=True))

        if not artiva_ids:
            self.stdout.write('No existing ArtivaLetters to reset.')
            return

        sa, _ = SessionsApproval.objects.filter(content_type=artiva_ct, object_id__in=artiva_ids).delete()
        ra, _ = RadiusApproval.objects.filter(content_type=artiva_ct, object_id__in=artiva_ids).delete()
        lv, _ = LetterVersion.objects.filter(content_type=artiva_ct, object_id__in=artiva_ids).delete()
        tk, _ = Ticket.objects.filter(content_type=artiva_ct, object_id__in=artiva_ids).delete()
        da, _ = DocumentAttachment.objects.filter(content_type=artiva_ct, object_id__in=artiva_ids).delete()
        try:
            cm, _ = Comment.objects.filter(content_type=artiva_ct, object_id__in=artiva_ids).delete()
        except Exception:
            cm = 0

        deleted_count, _ = ArtivaLetters.objects.all().delete()

        self.stdout.write(self.style.WARNING(
            f'RESET: deleted {deleted_count} ArtivaLetters record(s) and related '
            f'{sa} SessionsApproval, {ra} RadiusApproval, {lv} LetterVersion, '
            f'{tk} Ticket, {da} DocumentAttachment, {cm} Comment row(s).'
        ))

    def _bulk_create(self, rows, created_by):
        objs = []
        for r in rows:
            objs.append(ArtivaLetters(
                letter_code=r['letter_code'],
                creation_type=CREATION_TYPE,
                communication_type=COMMUNICATION_TYPE,
                communication_code=r['communication_code'],
                communication_subtype=r['communication_subtype'],
                timing=r['timing'],
                regulatory=r['regulatory'],
                priority=r['priority'],
                document_description=r['document_description'],
                production_date=PRODUCTION_DATE,
                source=r['source'],
                letter_description=r['letter_description'],
                system_type='ARTIVA',   # bulk_create bypasses save(), so set explicitly
                status=STATUS_VALUE,
                comments=IMPORT_COMMENT,
                created_by=created_by,
            ))

        ArtivaLetters.objects.bulk_create(objs, batch_size=200)
        return [o.letter_code for o in objs]

    def _create_sessions_approvals(self, letter_codes):
        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)
        letters = ArtivaLetters.objects.filter(letter_code__in=letter_codes)

        sessions = [
            SessionsApproval(
                content_type=artiva_ct,
                object_id=letter.id,
                approval_status='Approved',
                approval_date=make_aware(SESSIONS_APPROVAL_DATE),
                comments=IMPORT_COMMENT,
            )
            for letter in letters
        ]
        SessionsApproval.objects.bulk_create(sessions, batch_size=200)
        self.stdout.write(self.style.SUCCESS(
            f'Created {len(sessions)} SessionsApproval record(s), all Approved / {SESSIONS_APPROVAL_DATE.date()}.'
        ))

    def _create_radius_approvals(self, letter_codes, radius_approver):
        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)
        letters = ArtivaLetters.objects.filter(letter_code__in=letter_codes)

        radius_records = [
            RadiusApproval(
                content_type=artiva_ct,
                object_id=letter.id,
                cco_or_representative=radius_approver,
                approval_status='Approved',
                approval_date=make_aware(RADIUS_APPROVAL_DATE),
                comments=IMPORT_COMMENT,
            )
            for letter in letters
        ]
        RadiusApproval.objects.bulk_create(radius_records, batch_size=200)
        self.stdout.write(self.style.SUCCESS(
            f'Created {len(radius_records)} RadiusApproval record(s), all Approved / '
            f'{RADIUS_APPROVAL_DATE.date()} / CCO-Rep = {radius_approver.username}.'
        ))

    def _create_letter_versions(self, letter_codes, version_author):
        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)
        letters = list(ArtivaLetters.objects.filter(letter_code__in=letter_codes))

        versions = [
            LetterVersion(
                content_type=artiva_ct,
                object_id=letter.id,
                version_number=VERSION_NUMBER,
                version_author=version_author,
                version_note=VERSION_NOTE,
                version_data={
                    'letter_code': letter.letter_code,
                    'status': STATUS_VALUE,
                    'bulk_imported': True,
                },
                revision_reason=VERSION_REVISION_REASON,
                is_active=True,
            )
            for letter in letters
        ]
        LetterVersion.objects.bulk_create(versions, batch_size=200)

        # version_date and created_at are both auto_now_add=True, which bulk_create
        # doesn't respect the way we want (it stamps the real import time), so fix
        # them up afterward the same way we did for creation_revision_date.
        LetterVersion.objects.filter(
            content_type=artiva_ct, object_id__in=[letter.id for letter in letters]
        ).update(
            version_date=make_aware(COMPLETED_AT),
            created_at=make_aware(COMPLETED_AT),
        )

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(versions)} LetterVersion record(s) ({VERSION_NUMBER}), author = {version_author.username}.'
        ))