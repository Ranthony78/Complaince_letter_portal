# apps\letters\management\commands\attach_artiva_documents.py
r"""
ONE-TIME attach of physical document files to already-imported ArtivaLetters
records. Run this AFTER import_artiva_csv.py has created the letter rows.

MATCHING STRATEGY (tried in this order per letter):
  1. EXACT FILENAME: letter.document_description holds the exact original
     filename (e.g. "EM000024_Email.docx" for letter_code "ART-EM000024-0022").
     If a file with that exact name (case-insensitive) exists anywhere under
     --documents-folder, it's used. This is the most reliable match since it
     needs no pattern guessing.
  2. ID SEGMENT: if step 1 finds nothing, falls back to comparing the middle
     segment of "ART-{ID}-{seq}" style letter_codes against the filename with
     its extension and any trailing _Email/_Letter/_SMS suffix stripped
     (e.g. "ART-IDN000006-0001" -> "IDN000006", matched against
     "IDN000006_Email.docx" -> "IDN000006").
  3. EXACT STEM: if step 2 also finds nothing, falls back to comparing the
     filename stem directly against the full letter_code (old behavior, for
     letter_codes that don't follow the ART-{ID}-{seq} pattern at all).

Run manually by a developer from the terminal. Not exposed anywhere in the
app/UI.

--documents-folder is searched RECURSIVELY, so you can point it at a root
folder full of subfolders (e.g. "Email Letters\Email - Initial
Regulatory\IDN000006_Email.docx") and it will find files no matter which
subfolder they're in. Which subfolder a file sits in is not used for
anything by this script.

Usage (from project root, with venv active):

    Preview matches without copying/attaching anything:
        python manage.py attach_artiva_documents --documents-folder "C:\path\to\root\folder" --user gstevens --dry-run

    Actually attach:
        python manage.py attach_artiva_documents --documents-folder "C:\path\to\root\folder" --user gstevens

    Only process letters that don't already have a document attached (default):
        (this is the default behavior; already-attached letters are skipped)

    Re-attach even for letters that already have a document:
        python manage.py attach_artiva_documents --documents-folder "C:\path\to\root\folder" --user gstevens --force
"""
import os
import re

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from apps.letters.models import ArtivaLetters, DocumentAttachment

User = get_user_model()

DEFAULT_EXTENSIONS = ['pdf', 'doc', 'docx']
SUFFIX_PATTERN = re.compile(r'_(Email|Letter|SMS)$', re.IGNORECASE)


def id_from_filename(stem):
    """Strip a trailing _Email/_Letter/_SMS suffix from a filename stem to get the base ID."""
    return SUFFIX_PATTERN.sub('', stem).strip().lower()


def id_from_letter_code(letter_code):
    """Extract the middle segment from an 'ART-{ID}-{seq}' style letter_code.
    Returns None if the code doesn't have at least 3 hyphen-separated parts."""
    parts = letter_code.split('-')
    if len(parts) < 3:
        return None
    return '-'.join(parts[1:-1]).strip().lower()


class Command(BaseCommand):
    help = 'One-time attach of physical document files to ArtivaLetters records, matched by document_description/letter_code/filename.'

    def add_arguments(self, parser):
        parser.add_argument('--documents-folder', type=str, required=True,
                             help='Folder containing the document files')
        parser.add_argument('--user', type=str, required=True,
                             help='Username to set as uploaded_by for every attached document')
        parser.add_argument('--document-type', type=str, default='Original',
                             choices=['Original', 'Revision', 'Supporting', 'Client Response',
                                      'Approval Proof', 'Final', 'Legal', 'Other'],
                             help='DocumentAttachment.document_type value to use (default: Original)')
        parser.add_argument('--extensions', type=str, default=','.join(DEFAULT_EXTENSIONS),
                             help='Comma-separated list of file extensions to look for (default: pdf,doc,docx)')
        parser.add_argument('--dry-run', action='store_true',
                             help='Show what would be attached without touching the database or filesystem')
        parser.add_argument('--force', action='store_true',
                             help='Attach even if the letter already has a document of this type')

    def handle(self, *args, **options):
        folder = options['documents_folder']
        username = options['user']
        document_type = options['document_type']
        extensions = [e.strip().lower().lstrip('.') for e in options['extensions'].split(',') if e.strip()]
        dry_run = options['dry_run']
        force = options['force']

        if not os.path.isdir(folder):
            raise CommandError(f'Documents folder not found: {folder}')

        try:
            uploaded_by = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No user found with username '{username}'.")

        # Build two lookups of files anywhere under the folder (recursively):
        #   files_by_full_name: {lowercased "name.ext": full_path}  -- for exact
        #     document_description matches (primary strategy)
        #   files_by_id: {lowercased extracted ID: {ext: full_path}}  -- for the
        #     ID-segment and stem fallback strategies
        # If duplicates exist (e.g. the same filename appearing in two different
        # subfolders), the first one encountered wins and a warning is recorded.
        files_by_full_name = {}
        files_by_id = {}
        duplicate_warnings = []
        for dirpath, _dirnames, filenames in os.walk(folder):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                stem, ext = os.path.splitext(fname)
                ext = ext.lstrip('.').lower()
                if ext not in extensions:
                    continue

                full_name_key = fname.strip().lower()
                if full_name_key in files_by_full_name:
                    duplicate_warnings.append(
                        f'"{fname}" found in multiple places; keeping first match '
                        f'({files_by_full_name[full_name_key]}), ignoring {full_path}'
                    )
                else:
                    files_by_full_name[full_name_key] = full_path

                key = id_from_filename(stem)
                if key not in files_by_id:
                    files_by_id[key] = {}
                if ext not in files_by_id[key]:
                    files_by_id[key][ext] = full_path

        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)
        letters = ArtivaLetters.objects.all().order_by('letter_code')

        matched = []
        no_file = []
        already_has_doc = []
        matched_via = {'description': 0, 'id_segment': 0, 'stem_fallback': 0}

        for letter in letters:
            chosen_path = None

            # Strategy 1: exact filename match against document_description
            desc_key = (letter.document_description or '').strip().lower()
            if desc_key and desc_key in files_by_full_name:
                chosen_path = files_by_full_name[desc_key]
                matched_via['description'] += 1
            else:
                candidates = None
                # Strategy 2: match on the middle ID segment of ART-{ID}-{seq}
                code_id = id_from_letter_code(letter.letter_code)
                if code_id is not None and code_id in files_by_id:
                    candidates = files_by_id[code_id]
                    matched_via['id_segment'] += 1
                else:
                    # Strategy 3: exact filename-stem match against the full letter_code
                    fallback_key = letter.letter_code.strip().lower()
                    if fallback_key in files_by_id:
                        candidates = files_by_id[fallback_key]
                        matched_via['stem_fallback'] += 1

                if candidates is not None:
                    for ext in extensions:
                        if ext in candidates:
                            chosen_path = candidates[ext]
                            break

            if chosen_path is None:
                no_file.append(letter.letter_code)
                continue

            has_doc = DocumentAttachment.objects.filter(
                content_type=artiva_ct, object_id=letter.id
            ).exists()
            if has_doc and not force:
                already_has_doc.append(letter.letter_code)
                continue

            matched.append((letter, chosen_path))

        self.stdout.write(f'Letters checked: {letters.count()}')
        self.stdout.write(self.style.SUCCESS(f'  Matched to a file, ready to attach: {len(matched)}'))
        self.stdout.write(f"    via document_description exact match: {matched_via['description']}")
        self.stdout.write(f"    via ID-segment match: {matched_via['id_segment']}")
        self.stdout.write(f"    via exact-stem fallback: {matched_via['stem_fallback']}")
        self.stdout.write(self.style.WARNING(f'  No matching file found: {len(no_file)}'))
        self.stdout.write(f'  Already had a document (skipped, use --force to redo): {len(already_has_doc)}')

        if duplicate_warnings:
            self.stdout.write(self.style.WARNING(f'\n{len(duplicate_warnings)} duplicate filename(s) across subfolders:'))
            for w in duplicate_warnings[:20]:
                self.stdout.write(self.style.WARNING(f'  - {w}'))
            if len(duplicate_warnings) > 20:
                self.stdout.write(self.style.WARNING(f'  ... and {len(duplicate_warnings) - 20} more'))

        if no_file:
            self.stdout.write('\nLetters with NO matching file (first 20 shown):')
            for code in no_file[:20]:
                self.stdout.write(f'  - {code}')
            if len(no_file) > 20:
                self.stdout.write(f'  ... and {len(no_file) - 20} more')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n--dry-run: nothing was attached.'))
            if matched:
                self.stdout.write('Sample of what would be attached:')
                for letter, path in matched[:5]:
                    self.stdout.write(f'  {letter.letter_code} <- {path}')
            return

        attached_count = 0
        failed = []
        for letter, path in matched:
            try:
                with open(path, 'rb') as fh:
                    django_file = File(fh, name=os.path.basename(path))
                    doc = DocumentAttachment(
                        content_type=artiva_ct,
                        object_id=letter.id,
                        document_type=document_type,
                        description=f'Bulk attached document for {letter.letter_code}',
                        uploaded_by=uploaded_by,
                        is_current=True,
                    )
                    # .save(name, content, save=True) writes the file to storage AND
                    # calls doc.save(), which auto-fills file_name/file_size/file_type.
                    doc.file.save(django_file.name, django_file, save=True)
                attached_count += 1
            except Exception as e:
                failed.append((letter.letter_code, str(e)))

        self.stdout.write(self.style.SUCCESS(f'\nAttached {attached_count} document(s).'))
        if failed:
            self.stdout.write(self.style.ERROR(f'{len(failed)} failed:'))
            for code, err in failed:
                self.stdout.write(self.style.ERROR(f'  - {code}: {err}'))