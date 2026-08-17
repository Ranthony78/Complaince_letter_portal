# apps/letters/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import (
    FACSLetters, ArtivaLetters, Ticket, LetterVersion,
    DocumentAttachment, RadiusApproval, SessionsApproval, BaseLetter
)

User = get_user_model()

from django import forms
from django.utils import timezone
import re


class BaseLetterForm(forms.ModelForm):

    COMMON_FIELDS = [
        'communication_code',
        'communication_type',
        'creation_type',
        'communication_subtype',
        'letter_code',
        'regulatory',
        'timing',
        'priority',
        'production_date',
        'source',
        'letter_description',
    ]

    COMMON_WIDGETS = {
        'creation_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        'communication_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        'communication_code': forms.TextInput(attrs={'class': 'form-control'}),
        'communication_subtype': forms.Select(attrs={'class': 'form-select'}),
        'letter_code': forms.TextInput(attrs={'class': 'form-control'}),
        'regulatory': forms.Select(attrs={'class': 'form-select'}),
        'timing': forms.Select(attrs={'class': 'form-select'}),
        'priority': forms.Select(attrs={'class': 'form-select'}),
        'production_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        'source': forms.Select(attrs={'class': 'form-select'}),
        'letter_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    }

    COMMON_LABELS = {
        'communication_code': 'Letter/Email/SMS Code',
        'communication_type': 'Communication Type',
        'creation_type': 'Creation/Revision',
        'communication_subtype': 'Letter/Email/SMS',
        'letter_code': 'Letter Code',
        'regulatory': 'Regulatory',
        'timing': 'Timing',
        'priority': 'Priority',
        'production_date': 'Production Date',
        'source': 'Source',
        'letter_description': 'Letter Description',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bootstrap fix
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.RadioSelect, forms.CheckboxInput)):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

        # Common dropdowns
        self.fields['regulatory'].choices = [('', 'Select'), ('Yes', 'Yes'), ('No', 'No')]
        self.fields['timing'].choices = [('', 'Select'), ('Initial', 'Initial'), ('Subsequent', 'Subsequent'), ('Seasonal', 'Seasonal')]
        self.fields['source'].choices = [('', 'Select'), ('Internal', 'Internal'), ('LiveVox', 'LiveVox'), ('CompuMail', 'CompuMail'), ('RevSpring', 'RevSpring')]
        self.fields['communication_subtype'].choices = [('', 'Select'), ('Letter', 'Letter'), ('Email', 'Email'), ('SMS', 'SMS')]
        self.fields['priority'].choices = [('', 'Select'), ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Critical', 'Critical')]

        # Make optional
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned = super().clean()

        # Communication code validation
        code = cleaned.get('communication_code')
        if code and not re.match(r'^[A-Z0-9\-_]+$', code, re.IGNORECASE):
            raise forms.ValidationError("Invalid Communication Code format")

        return cleaned


class FACSCreationForm(forms.ModelForm):
    """Form for creating FACS letters with client approval matrix"""

    class Meta:
        model = FACSLetters
        fields = [
            'communication_code',
            'communication_type',
            'creation_type',
            'communication_subtype',
            'letter_code',
            'regulatory',
            'timing',
            'production_date',
            'source',
            'letter_description',
            'priority',
            'ticket_number',
            'ticket_open_date',
            'ticket_completed_date',
        ]
        widgets = {
            'creation_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'communication_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'communication_code': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g., LTR-2024-001, Email-FACS-001, SMS-COMP-001'}),
            'communication_subtype': forms.Select(attrs={'class': 'form-select'}),
            'letter_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter letter code'}),
            'regulatory': forms.Select(attrs={'class': 'form-select'}),
            'timing': forms.Select(attrs={'class': 'form-select'}),
            'production_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'letter_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                        'placeholder': 'Detailed description of the letter content'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'ticket_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter ticket number'}),
            'ticket_open_date': forms.DateTimeInput(
                attrs={'class': 'form-control datetimepicker', 'type': 'datetime-local'}),
            'ticket_completed_date': forms.DateTimeInput(
                attrs={'class': 'form-control datetimepicker', 'type': 'datetime-local'}),
        }
        labels = {
            'communication_code': 'Letter/Email/SMS Code',
            'communication_type': 'Communication Type',
            'creation_type': 'Creation/Revision',
            'communication_subtype': 'Letter/Email/SMS',
            'letter_code': 'Letter Code',
            'regulatory': 'Regulatory',
            'timing': 'Timing',
            'production_date': 'Production Date',
            'source': 'Source',
            'letter_description': 'Letter Description',
            'priority': 'Priority',
            'ticket_number': 'Ticket #',
            'ticket_open_date': 'Ticket Open Date',
            'ticket_completed_date': 'Ticket Completed Date',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.RadioSelect, forms.CheckboxInput)):
                if not field.widget.attrs.get('class'):
                    field.widget.attrs['class'] = ''
                field.widget.attrs['class'] += ' form-control'

        # Set regulatory choices
        self.fields['regulatory'].choices = [
            ('', 'Select'),
            ('Yes', 'Yes'),
            ('No', 'No'),
        ]

        # Set timing choices for FACS
        self.fields['timing'].choices = [
            ('', 'Select Timing'),
            ('Initial', 'Initial'),
            ('Subsequent', 'Subsequent'),
            ('Seasonal', 'Seasonal'),
        ]

        # Set source choices
        self.fields['source'].choices = [
            ('', 'Select Source'),
            ('Internal', 'Internal'),
            ('LiveVox', 'LiveVox'),
            ('CompuMail', 'CompuMail'),
            ('RevSpring', 'RevSpring'),
        ]

        # Set communication subtype choices
        self.fields['communication_subtype'].choices = [
            ('', 'Select'),
            ('Letter', 'Letter'),
            ('Email', 'Email'),
            ('SMS', 'SMS'),
        ]

        # Set priority choices
        self.fields['priority'].choices = [
            ('', 'Select'),
            ('Low', 'Low'),
            ('Medium', 'Medium'),
            ('High', 'High'),
            ('Critical', 'Critical'),
        ]

        # Remove required attribute from fields to allow blank selection
        self.fields['regulatory'].required = False
        self.fields['timing'].required = False
        self.fields['source'].required = False
        self.fields['priority'].required = False
        self.fields['communication_subtype'].required = False

    def clean(self):
        cleaned_data = super().clean()


        # Validate communication code format
        comm_code = cleaned_data.get('communication_code')
        if comm_code and not self.validate_communication_code(comm_code):
            raise forms.ValidationError(
                "Communication Code should contain only letters, numbers, hyphens, and underscores.")

        return cleaned_data

    def validate_communication_code(self, code):
        """Validate communication code format"""
        import re
        return bool(re.match(r'^[A-Z0-9\-_]+$', code, re.IGNORECASE))


class ArtivaCreationForm(forms.ModelForm):
    """Form for creating Artiva letters"""

    class Meta:
        model = ArtivaLetters
        fields = [
            'communication_code',
            'communication_type',
            'creation_type',
            'communication_subtype',
            'letter_code',
            'regulatory',
            'timing',
            'priority',
            'production_date',
            'source',
            'letter_description',
        ]
        widgets = {
            'creation_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'communication_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'communication_code': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter communication code'}),
            'communication_subtype': forms.Select(attrs={'class': 'form-select'}),
            'letter_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter letter code'}),
            'regulatory': forms.Select(attrs={'class': 'form-select'}),
            'timing': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'production_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'letter_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                        'placeholder': 'Detailed description of the letter content'}),
        }
        labels = {
            'communication_code': 'Letter/Email/SMS Code',
            'communication_type': 'Communication Type',
            'creation_type': 'Creation/Revision',
            'communication_subtype': 'Letter/Email/SMS',
            'letter_code': 'Letter Code',
            'regulatory': 'Regulatory',
            'timing': 'Timing',
            'priority': 'Priority',
            'production_date': 'Production Date',
            'source': 'Source',
            'letter_description': 'Letter Description',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.RadioSelect, forms.CheckboxInput)):
                if not field.widget.attrs.get('class'):
                    field.widget.attrs['class'] = ''
                field.widget.attrs['class'] += ' form-control'

        # Set regulatory choices
        self.fields['regulatory'].choices = [
            ('', 'Select Regulatory'),
            ('Yes', 'Yes'),
            ('No', 'No'),
        ]

        # Set timing choices for Artiva
        self.fields['timing'].choices = [
            ('', 'Select Timing'),
            ('Initial', 'Initial'),
            ('Subsequent', 'Subsequent'),
            ('Seasonal', 'Seasonal'),
        ]

        # Set source choices
        self.fields['source'].choices = [
            ('', 'Select Source'),
            ('Internal', 'Internal'),
            ('LiveVox', 'LiveVox'),
            ('CompuMail', 'CompuMail'),
            ('RevSpring', 'RevSpring'),
        ]

        # Set communication subtype choices
        self.fields['communication_subtype'].choices = [
            ('', 'Select Type'),
            ('Letter', 'Letter'),
            ('Email', 'Email'),
            ('SMS', 'SMS'),
        ]

        # Set priority choices
        self.fields['priority'].choices = [
            ('', 'Select Priority'),
            ('Low', 'Low'),
            ('Medium', 'Medium'),
            ('High', 'High'),
            ('Critical', 'Critical'),
        ]

        # Make all fields optional
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned_data = super().clean()


        # FIX: Don't validate communication_code if it's not changed or is being preserved
        comm_code = cleaned_data.get('communication_code')
        # Also check from initial data
        if not comm_code and self.instance and self.instance.communication_code:
            comm_code = self.instance.communication_code
            cleaned_data['communication_code'] = comm_code

        if comm_code and not self.validate_communication_code(comm_code):
            raise forms.ValidationError(
                "Communication Code should contain only letters, numbers, hyphens, and underscores."
            )

        return cleaned_data

    def validate_communication_code(self, code):
        """Validate communication code format"""
        import re
        return bool(re.match(r'^[A-Z0-9\-_]+$', code, re.IGNORECASE))


class TicketForm(forms.ModelForm):
    """Form for managing tickets associated with letters"""

    ticket_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter ticket number'}),
        label='Ticket #'
    )
    open_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control datetimepicker', 'type': 'datetime-local'}),
        label='Ticket Open Date'
    )
    completed_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control datetimepicker', 'type': 'datetime-local'}),
        label='Ticket Completed Date'
    )

    class Meta:
        model = Ticket
        fields = ['ticket_number', 'open_date', 'completed_date', 'assigned_to', 'notes', 'status', 'priority']
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-select select2'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'assigned_to': 'Assigned To',
            'notes': 'Notes',
            'status': 'Ticket Status',
            'priority': 'Ticket Priority',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set status choices
        self.fields['status'].choices = [
            ('Open', 'Open'),
            ('In Progress', 'In Progress'),
            ('Pending', 'Pending'),
            ('Resolved', 'Resolved'),
            ('Closed', 'Closed'),
        ]

        # Set priority choices
        self.fields['priority'].choices = [
            ('', 'Select Priority'),
            ('Low', 'Low'),
            ('Medium', 'Medium'),
            ('High', 'High'),
            ('Critical', 'Critical'),
        ]

        # Limit assigned_to to active users
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        self.fields['assigned_to'].empty_label = 'Select user...'

    def clean(self):
        cleaned_data = super().clean()
        open_date = cleaned_data.get('open_date')
        completed_date = cleaned_data.get('completed_date')

        if completed_date and open_date and completed_date < open_date:
            raise forms.ValidationError("Completed date cannot be before open date.")

        return cleaned_data


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading documents and attachments"""

    document_type = forms.ChoiceField(
        choices=[
            ('Original', 'Original Document'),
            ('Revision', 'Revision Document'),
            ('Supporting', 'Supporting Document'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Document Type'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description'}),
        label='Description'
    )

    class Meta:
        model = DocumentAttachment
        fields = ['file', 'document_type', 'description', 'is_current']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.png'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'file': 'Upload Document',
            'is_current': 'Set as current version',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].help_text = "Supported formats: PDF, DOC, DOCX (Max 10MB)"

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size cannot exceed 10MB.")

            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx']
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError(f"File type not allowed. Allowed types: PDF, DOC, DOCX")

        return file


class LetterVersionForm(forms.ModelForm):
    """Form for creating new letter versions"""

    class Meta:
        model = LetterVersion
        fields = ['version_note', 'revision_reason', 'pdf_copy']
        widgets = {
            'version_note': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the changes in this version'}),
            'revision_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for revision'}),
            'pdf_copy': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
        }
        labels = {
            'version_note': 'Version Notes',
            'revision_reason': 'Revision Reason',
            'pdf_copy': 'Upload PDF Copy',
        }


class RadiusApprovalForm(forms.ModelForm):
    """Form for Radius approval"""

    class Meta:
        model = RadiusApproval
        fields = ['cco_or_representative', 'comments']
        widgets = {
            'cco_or_representative': forms.Select(attrs={'class': 'form-select select2'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional comments'}),
        }
        labels = {
            'cco_or_representative': 'CCO or Representative',
            'comments': 'Comments',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit to CCO and Representatives only - FIXED
        from apps.accounts.models import User
        self.fields['cco_or_representative'].queryset = User.objects.filter(
            role__in=['CCO', 'Representative'],
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        # Set empty label
        self.fields['cco_or_representative'].empty_label = 'Select CCO or Representative'


class SessionsApprovalForm(forms.ModelForm):
    """Form for Sessions approval"""

    class Meta:
        model = SessionsApproval
        fields = ['session_reference', 'comments']
        widgets = {
            'session_reference': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter session reference'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional comments'}),
        }
        labels = {
            'session_reference': 'Session Reference',
            'comments': 'Comments',
        }


class ClientApprovalForm(forms.Form):
    """Form for client approval in FACS system"""

    client_name = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    contact_person = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact person name'})
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional comments'})
    )

    def __init__(self, *args, **kwargs):
        pending_clients = kwargs.pop('pending_clients', [])
        super().__init__(*args, **kwargs)

        if pending_clients:
            self.fields['client_name'].choices = [(client, client) for client in pending_clients]
        else:
            self.fields['client_name'].choices = [('', 'No pending clients')]


class CCOFinalApprovalForm(forms.Form):
    """Form for final CCO approval"""

    comments = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter final approval comments'})
    )
    action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve and Lock'),
            ('reject', 'Return for Revision'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comments'].label = "Final Comments"


class LetterSearchForm(forms.Form):
    """Form for searching and filtering letters"""

    letter_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by letter code'})
    )
    system_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Systems'), ('FACS', 'FACS'), ('ARTIVA', 'Artiva')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'})
    )
    created_by = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="All Users"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set status choices from model
        self.fields['status'].choices = [('', 'All Status')] + list(BaseLetter.STATUS_CHOICES)



class DateRangeForm(forms.Form):
    """Form for date range selection in reports"""

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'})
    )
    report_type = forms.ChoiceField(
        choices=[
            ('summary', 'Summary Report'),
            ('detailed', 'Detailed Report'),
            ('approval', 'Approval Report'),
            ('timeline', 'Timeline Report'),
            ('client', 'Client Approval Report'),
            ('version', 'Version History Report'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date.")

        return cleaned_data


class DelegateLetterForm(forms.Form):
    """Form for delegating letter creation/revision to another user"""

    delegate_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, role__in=['Representative', 'InternalReviewer']),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select user"
    )
    delegation_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Instructions for the delegate'})
    )
    deadline = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control datetimepicker', 'type': 'datetime-local'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delegate_to'].label = "Delegate To"
        self.fields['delegation_notes'].label = "Instructions"
        self.fields['deadline'].label = "Completion Deadline"


class BulkApprovalForm(forms.Form):
    """Form for bulk approvals (CCO only)"""

    letters = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter comments for all selected letters'})
    )
    approval_action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve All'),
            ('reject', 'Reject All'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        letters_queryset = kwargs.pop('letters_queryset', None)
        super().__init__(*args, **kwargs)

        if letters_queryset:
            self.fields['letters'].queryset = letters_queryset
            self.fields['letters'].label_from_instance = lambda \
                obj: f"{obj.letter_code} - {obj.document_description[:50]}"