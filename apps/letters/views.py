from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Q, Count, Avg, Sum, F
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.http import require_POST
from django.http import Http404
import json
import os

from .models import FACSLetters, ArtivaLetters, RadiusApproval, SessionsApproval, Ticket, LetterVersion, \
    DocumentAttachment
from .forms import (
    FACSCreationForm, ArtivaCreationForm, TicketForm, DocumentUploadForm,
    LetterVersionForm, RadiusApprovalForm, SessionsApprovalForm,
    ClientApprovalForm, CCOFinalApprovalForm, LetterSearchForm,
    DateRangeForm, DelegateLetterForm, BulkApprovalForm
)
from apps.accounts.models import User, Notification, UserActivityLog


class LetterListView(LoginRequiredMixin, ListView):
    """List all letters with filtering"""
    template_name = 'letters/list.html'
    context_object_name = 'letters'
    paginate_by = 25

    def get_queryset(self):
        # Get all letters from both models
        facs_letters = FACSLetters.objects.all().select_related('created_by')
        artiva_letters = ArtivaLetters.objects.all().select_related('created_by')

        # Combine and sort
        all_letters = list(facs_letters) + list(artiva_letters)
        all_letters.sort(key=lambda x: x.created_at, reverse=True)

        # Apply filters if any
        system_filter = self.request.GET.get('system')
        if system_filter:
            all_letters = [l for l in all_letters if l.system_type == system_filter]

        status_filter = self.request.GET.get('status')
        if status_filter:
            all_letters = [l for l in all_letters if l.status == status_filter]

        search_query = self.request.GET.get('search')
        if search_query:
            all_letters = [l for l in all_letters if
                           search_query.lower() in l.letter_code.lower() or
                           search_query.lower() in (l.document_description or '').lower() or
                           search_query.lower() in (l.letter_description or '').lower()]

        return all_letters

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = LetterSearchForm(self.request.GET)
        context['total_facs'] = FACSLetters.objects.count()
        context['total_artiva'] = ArtivaLetters.objects.count()

        # Add stats for summary cards
        all_letters = self.get_queryset()
        context['total_letters'] = len(all_letters)
        context['completed_count'] = len([l for l in all_letters if l.status == 'Completed'])
        context['pending_count'] = len([l for l in all_letters if
                                        l.status in ['Radius_Pending', 'Sessions_Pending', 'Client_Pending',
                                                     'CCO_Review']])
        context['draft_count'] = len([l for l in all_letters if l.status == 'Draft'])

        return context


class MyDraftsView(LoginRequiredMixin, ListView):
    """View user's draft letters"""
    template_name = 'letters/drafts.html'
    context_object_name = 'drafts'
    paginate_by = 25

    def get_queryset(self):
        facs_drafts = FACSLetters.objects.filter(
            created_by=self.request.user,
            status='Draft'
        )
        artiva_drafts = ArtivaLetters.objects.filter(
            created_by=self.request.user,
            status='Draft'
        )

        all_drafts = list(facs_drafts) + list(artiva_drafts)
        all_drafts.sort(key=lambda x: x.created_at, reverse=True)

        return all_drafts


class LetterSearchView(LoginRequiredMixin, TemplateView):
    """Search letters"""
    template_name = 'letters/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')

        if query:
            facs_results = FACSLetters.objects.filter(
                Q(letter_code__icontains=query) |
                Q(document_description__icontains=query) |
                Q(letter_description__icontains=query)
            )

            artiva_results = ArtivaLetters.objects.filter(
                Q(letter_code__icontains=query) |
                Q(document_description__icontains=query) |
                Q(letter_description__icontains=query)
            )

            context['facs_results'] = facs_results
            context['artiva_results'] = artiva_results
            context['query'] = query
            context['total_results'] = facs_results.count() + artiva_results.count()

        return context


class CreateFACSLetterView(LoginRequiredMixin, CreateView):
    """Create a new FACS letter"""
    model = FACSLetters
    form_class = FACSCreationForm
    template_name = 'letters/create_facs.html'
    success_url = reverse_lazy('letters:list')

    def form_valid(self, form):
        """Handle valid form submission"""
        from datetime import datetime
        from django.utils import timezone
        from django.contrib.contenttypes.models import ContentType
        from .models import Ticket, DocumentAttachment, RadiusApproval, SessionsApproval

        form.instance.created_by = self.request.user
        form.instance.system_type = 'FACS'

        # Set creation_revision_date with timezone-aware datetime
        form.instance.creation_revision_date = timezone.now()

        # Save the letter first
        response = super().form_valid(form)
        letter = form.instance

        # ========== HANDLE CLIENT APPROVALS ==========
        client_approvals = {}

        # Define all possible clients
        clients = ['US Bank', 'US Bank Retail', 'Discover', 'Wells Fargo', 'Capital One']

        # Process each client
        for client in clients:
            # Check if client was selected (checkbox name format: client_Client_Name)
            client_field_name = f"client_{client.replace(' ', '_').lower()}"
            if self.request.POST.get(client_field_name):
                # Get contact person
                #contact_field = f"client_contact_{client.replace(' ', '_').lower()}"
                #contact = self.request.POST.get(contact_field, '')
                contact = ''  # Disabled contact field

                client_approvals[client] = {
                    'status': 'Pending',
                    'date': None,
                    'contact': contact,
                    'comments': ''
                }

        # Handle custom client (Client Approval 6)
        if self.request.POST.get('client_custom'):
            custom_name = self.request.POST.get('client_custom_name', '')
            custom_contact = self.request.POST.get('client_contact_custom', '')

            if custom_name:
                client_approvals['Client Approval 6'] = {
                    'status': 'Pending',
                    'date': None,
                    'contact': custom_contact,
                    'custom_name': custom_name,
                    'comments': ''
                }

        # Save client approvals to the letter
        if client_approvals:
            letter.client_approvals = client_approvals
            letter.save()

        # ========== HANDLE TICKET INFORMATION ==========
        ticket_number = self.request.POST.get('ticket_number')
        ticket_open_date = self.request.POST.get('ticket_open_date')
        ticket_completed_date = self.request.POST.get('ticket_completed_date')
        ticket_notes = self.request.POST.get('ticket_notes', '')

        if ticket_number or ticket_open_date:
            # Convert ticket dates to timezone-aware
            open_date = None
            if ticket_open_date:
                try:
                    open_date = timezone.make_aware(datetime.strptime(ticket_open_date, '%Y-%m-%dT%H:%M'))
                except (ValueError, TypeError):
                    open_date = timezone.now()

            completed_date = None
            if ticket_completed_date:
                try:
                    completed_date = timezone.make_aware(datetime.strptime(ticket_completed_date, '%Y-%m-%dT%H:%M'))
                except (ValueError, TypeError):
                    pass

            Ticket.objects.create(
                content_type=ContentType.objects.get_for_model(letter),
                object_id=letter.id,
                ticket_number=ticket_number or f"TKT-{letter.id}",
                open_date=open_date or timezone.now(),
                completed_date=completed_date,
                status='Open',
                notes=ticket_notes
            )

        # ========== HANDLE DOCUMENT UPLOAD ==========
        if self.request.FILES.get('document'):
            doc_file = self.request.FILES['document']
            doc = DocumentAttachment.objects.create(
                content_type=ContentType.objects.get_for_model(letter),
                object_id=letter.id,
                file=doc_file,
                file_name=doc_file.name,
                file_type=doc_file.name.split('.')[-1].lower(),
                document_type=self.request.POST.get('document_type', 'Original'),
                description=self.request.POST.get('document_description', ''),
                uploaded_by=self.request.user,
                is_current=True
            )

        # ========== HANDLE APPROVAL DATES (CCO ONLY) ==========
        # FIX: Only create approval records if user is NOT submitting for review
        # The submit_for_review function will create them when needed
        action = self.request.POST.get('action')

        if self.request.user.role == 'CCO' and action != 'submit':
            # Only create approval records if CCO is NOT submitting (i.e., saving as draft)
            # This prevents duplicate approval records
            radius_approval_date = self.request.POST.get('radius_approval_date')
            cco_representative_id = self.request.POST.get('cco_representative')
            approval_comments = self.request.POST.get('approval_comments', '')

            if cco_representative_id:
                try:
                    radius_approval, created = RadiusApproval.objects.get_or_create(
                        content_type=ContentType.objects.get_for_model(letter),
                        object_id=letter.id,
                        defaults={
                            'cco_or_representative_id': cco_representative_id,
                            'approval_status': 'Approved' if radius_approval_date else 'Pending',
                            'comments': approval_comments
                        }
                    )

                    if radius_approval_date:
                        # Convert date to timezone-aware datetime
                        date_obj = datetime.strptime(radius_approval_date, '%Y-%m-%d').date()
                        # Set to noon to avoid timezone issues
                        aware_datetime = timezone.make_aware(
                            datetime.combine(date_obj, datetime.min.time())
                        )
                        radius_approval.approval_date = aware_datetime
                        radius_approval.approval_status = 'Approved'
                        radius_approval.comments = approval_comments
                        radius_approval.save()
                    elif not created and not radius_approval.approval_date:
                        radius_approval.approval_status = 'Pending'
                        radius_approval.save()
                except Exception as e:
                    print(f"Error saving radius approval: {e}")

            # Handle Sessions Approval
            sessions_approval_date = self.request.POST.get('sessions_approval_date')
            if sessions_approval_date:
                try:
                    sessions_approval, created = SessionsApproval.objects.get_or_create(
                        content_type=ContentType.objects.get_for_model(letter),
                        object_id=letter.id,
                        defaults={
                            'approval_status': 'Approved',
                            'comments': approval_comments
                        }
                    )
                    # Convert date to timezone-aware datetime
                    date_obj = datetime.strptime(sessions_approval_date, '%Y-%m-%d').date()
                    aware_datetime = timezone.make_aware(
                        datetime.combine(date_obj, datetime.min.time())
                    )
                    sessions_approval.approval_date = aware_datetime
                    sessions_approval.approval_status = 'Approved'
                    sessions_approval.comments = approval_comments
                    sessions_approval.save()
                except Exception as e:
                    print(f"Error saving sessions approval: {e}")

        # ========== HANDLE FORM FIELDS THAT MIGHT BE MISSING ==========
        # Set default values for optional fields
        if not letter.priority:
            letter.priority = 'Medium'
        if not letter.regulatory:
            letter.regulatory = 'No'
        if not letter.timing:
            letter.timing = 'Initial'
        if not letter.source:
            letter.source = 'Internal'

        # Save letter again if defaults were set
        letter.save()

        # ========== CREATE NOTIFICATION ==========
        Notification.objects.create(
            user=self.request.user,
            type='system_alert',
            title='FACS Letter Created',
            message=f'Your FACS letter {letter.letter_code} has been created successfully.',
            link=reverse('letters:facs_detail', args=[letter.id])
        )

        messages.success(self.request, f'FACS letter {letter.letter_code} created successfully!')

        # Check if submitted for review
        if action == 'submit':
            return redirect('letters:submit_for_review', pk=letter.id)
        else:
            return redirect('letters:facs_detail', pk=letter.id)

        return response

    def form_invalid(self, form):
        """Handle invalid form submission"""
        # Print errors for debugging
        print("Form errors:", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")

        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['system_type'] = 'FACS'

        # Add CCO and Representative users for the dropdown
        from apps.accounts.models import User
        context['cco_users'] = User.objects.filter(
            role__in=['CCO', 'Representative'],
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        # If editing existing letter, load existing approval data
        if self.object:
            try:
                radius_approval = RadiusApproval.objects.get(
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.id
                )
                context['radius_approval'] = radius_approval
                context['radius_approval_date'] = radius_approval.approval_date.strftime(
                    '%Y-%m-%d') if radius_approval.approval_date else ''
                context['approval_comments'] = radius_approval.comments
            except RadiusApproval.DoesNotExist:
                pass

            try:
                sessions_approval = SessionsApproval.objects.get(
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.id
                )
                context['sessions_approval_date'] = sessions_approval.approval_date.strftime(
                    '%Y-%m-%d') if sessions_approval.approval_date else ''
            except SessionsApproval.DoesNotExist:
                pass

        return context


class CreateArtivaLetterView(LoginRequiredMixin, CreateView):
    """Create a new Artiva letter"""
    model = ArtivaLetters
    form_class = ArtivaCreationForm
    template_name = 'letters/create_artiva.html'
    success_url = reverse_lazy('letters:list')

    def form_valid(self, form):
        """Handle valid form submission"""
        from datetime import datetime
        from django.utils import timezone
        from django.contrib.contenttypes.models import ContentType
        from .models import Ticket, DocumentAttachment, RadiusApproval, SessionsApproval

        form.instance.created_by = self.request.user
        form.instance.system_type = 'ARTIVA'

        # Set creation_revision_date with timezone-aware datetime
        form.instance.creation_revision_date = timezone.now()

        # Save the letter first
        response = super().form_valid(form)
        letter = form.instance

        # ========== HANDLE TICKET INFORMATION ==========
        ticket_number = self.request.POST.get('ticket_number')
        ticket_open_date = self.request.POST.get('ticket_open_date')
        ticket_completed_date = self.request.POST.get('ticket_completed_date')
        ticket_notes = self.request.POST.get('ticket_notes', '')

        # Always set open_date (default to now if not provided)
        open_date = None
        if ticket_open_date:
            try:
                open_date = timezone.make_aware(datetime.strptime(ticket_open_date, '%Y-%m-%dT%H:%M'))
            except (ValueError, TypeError):
                open_date = timezone.now()
        else:
            open_date = timezone.now()  # Default to now

        completed_date = None
        if ticket_completed_date:
            try:
                completed_date = timezone.make_aware(datetime.strptime(ticket_completed_date, '%Y-%m-%dT%H:%M'))
            except (ValueError, TypeError):
                pass

        Ticket.objects.create(
            content_type=ContentType.objects.get_for_model(letter),
            object_id=letter.id,
            ticket_number=ticket_number or f"TKT-{letter.id}",
            open_date=open_date,  # ADD THIS - always set
            completed_date=completed_date,
            status='Open',
            notes=ticket_notes
        )

        # ========== HANDLE DOCUMENT UPLOAD ==========
        if self.request.FILES.get('document'):
            doc_file = self.request.FILES['document']
            doc = DocumentAttachment.objects.create(
                content_type=ContentType.objects.get_for_model(letter),
                object_id=letter.id,
                file=doc_file,
                file_name=doc_file.name,
                file_type=doc_file.name.split('.')[-1].lower(),
                document_type=self.request.POST.get('document_type', 'Original'),
                description=self.request.POST.get('document_description', ''),
                uploaded_by=self.request.user,
                is_current=True
            )

        # ========== HANDLE APPROVAL DATES (CCO ONLY) ==========
        # Only create approval records if user is NOT submitting for review
        # The submit_for_review function will create them when needed
        action = self.request.POST.get('action')

        if self.request.user.role == 'CCO' and action != 'submit':
            # Only create approval records if CCO is NOT submitting (i.e., saving as draft)
            # This prevents duplicate approval records
            radius_approval_date = self.request.POST.get('radius_approval_date')
            cco_representative_id = self.request.POST.get('cco_representative')
            approval_comments = self.request.POST.get('approval_comments', '')

            if cco_representative_id:
                try:
                    radius_approval, created = RadiusApproval.objects.get_or_create(
                        content_type=ContentType.objects.get_for_model(letter),
                        object_id=letter.id,
                        defaults={
                            'cco_or_representative_id': cco_representative_id,
                            'approval_status': 'Approved' if radius_approval_date else 'Pending',
                            'comments': approval_comments
                        }
                    )

                    if radius_approval_date:
                        # Convert date to timezone-aware datetime
                        date_obj = datetime.strptime(radius_approval_date, '%Y-%m-%d').date()
                        # Set to noon to avoid timezone issues
                        aware_datetime = timezone.make_aware(
                            datetime.combine(date_obj, datetime.min.time())
                        )
                        radius_approval.approval_date = aware_datetime
                        radius_approval.approval_status = 'Approved'
                        radius_approval.comments = approval_comments
                        radius_approval.save()
                    elif not created and not radius_approval.approval_date:
                        radius_approval.approval_status = 'Pending'
                        radius_approval.save()
                except Exception as e:
                    print(f"Error saving radius approval: {e}")

            # Handle Sessions Approval
            sessions_approval_date = self.request.POST.get('sessions_approval_date')
            if sessions_approval_date:
                try:
                    sessions_approval, created = SessionsApproval.objects.get_or_create(
                        content_type=ContentType.objects.get_for_model(letter),
                        object_id=letter.id,
                        defaults={
                            'approval_status': 'Approved',
                            'comments': approval_comments
                        }
                    )
                    # Convert date to timezone-aware datetime
                    date_obj = datetime.strptime(sessions_approval_date, '%Y-%m-%d').date()
                    aware_datetime = timezone.make_aware(
                        datetime.combine(date_obj, datetime.min.time())
                    )
                    sessions_approval.approval_date = aware_datetime
                    sessions_approval.approval_status = 'Approved'
                    sessions_approval.comments = approval_comments
                    sessions_approval.save()
                except Exception as e:
                    print(f"Error saving sessions approval: {e}")

        # ========== HANDLE FORM FIELDS THAT MIGHT BE MISSING ==========
        # Set default values for optional fields
        if not letter.priority:
            letter.priority = 'Medium'
        if not letter.regulatory:
            letter.regulatory = 'No'
        if not letter.timing:
            letter.timing = 'Initial'
        if not letter.source:
            letter.source = 'Internal'

        # Save letter again if defaults were set
        letter.save()

        # ========== CREATE NOTIFICATION ==========
        Notification.objects.create(
            user=self.request.user,
            type='system_alert',
            title='Artiva Letter Created',
            message=f'Your Artiva letter {letter.letter_code} has been created successfully.',
            link=reverse('letters:artiva_detail', args=[letter.id])
        )

        messages.success(self.request, f'Artiva letter {letter.letter_code} created successfully!')

        # Check if submitted for review
        if action == 'submit':
            return redirect('letters:submit_for_review', pk=letter.id)
        else:
            return redirect('letters:artiva_detail', pk=letter.id)

        return response

    def form_invalid(self, form):
        """Handle invalid form submission"""
        # Print errors for debugging
        print("Form errors:", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")

        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['system_type'] = 'ARTIVA'

        # Add CCO and Representative users for the dropdown
        from apps.accounts.models import User
        context['cco_users'] = User.objects.filter(
            role__in=['CCO', 'Representative'],
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        # If editing existing letter, load existing approval data
        if self.object:
            try:
                radius_approval = RadiusApproval.objects.get(
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.id
                )
                context['radius_approval'] = radius_approval
                context['radius_approval_date'] = radius_approval.approval_date.strftime(
                    '%Y-%m-%d') if radius_approval.approval_date else ''
                context['approval_comments'] = radius_approval.comments
            except RadiusApproval.DoesNotExist:
                pass

            try:
                sessions_approval = SessionsApproval.objects.get(
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.id
                )
                context['sessions_approval_date'] = sessions_approval.approval_date.strftime(
                    '%Y-%m-%d') if sessions_approval.approval_date else ''
            except SessionsApproval.DoesNotExist:
                pass

        return context


class LetterDetailView(LoginRequiredMixin, DetailView):
    """Generic letter detail view"""
    template_name = 'letters/detail.html'

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')

        # Try to get as FACS first, then Artiva
        try:
            return FACSLetters.objects.get(pk=pk)
        except FACSLetters.DoesNotExist:
            try:
                return ArtivaLetters.objects.get(pk=pk)
            except ArtivaLetters.DoesNotExist:
                raise Http404("No letter found with this ID.")

    def get_template_names(self):
        """Return different template based on letter type"""
        if isinstance(self.object, FACSLetters):
            return ['letters/facs_detail.html']
        else:
            return ['letters/artiva_detail.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        letter = self.object

        # FIX: Add 'letter' to context for templates that expect it
        context['letter'] = letter
        context['object'] = letter  # Also keep object for compatibility

        # Get related data
        content_type = ContentType.objects.get_for_model(letter)

        # Get Radius Approval
        try:
            radius_approval = RadiusApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['radius_approval'] = radius_approval
        except RadiusApproval.DoesNotExist:
            context['radius_approval'] = None

        # Get Sessions Approval
        try:
            sessions_approval = SessionsApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['sessions_approval'] = sessions_approval
        except SessionsApproval.DoesNotExist:
            context['sessions_approval'] = None

        # Get Ticket
        try:
            context['ticket'] = Ticket.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
        except Ticket.DoesNotExist:
            context['ticket'] = None

        # Get versions and documents
        context['versions'] = LetterVersion.objects.filter(
            content_type=content_type,
            object_id=letter.id
        )

        context['documents'] = DocumentAttachment.objects.filter(
            content_type=content_type,
            object_id=letter.id
        )

        # For FACS letters, get client approval data
        if isinstance(letter, FACSLetters):
            context['client_approvals'] = letter.get_client_approval_matrix()
            context['approval_percentage'] = letter.get_approval_percentage()
            context['pending_clients'] = letter.get_pending_clients()
        else:
            # Artiva letters don't have client approvals
            context['client_approvals'] = {}
            context['approval_percentage'] = 0
            context['pending_clients'] = []

        # Check if user can approve and determine approval type
        context['can_approve'] = self.check_approval_permission(letter)
        context['approval_type'] = self.get_approval_type(letter)

        return context

    def check_approval_permission(self, letter):
        user = self.request.user
        if user.role == 'CCO':
            return True
        if letter.status == 'Radius_Pending' and user.has_perm('accounts.can_approve_radius'):
            return True
        if letter.status == 'Sessions_Pending' and user.has_perm('accounts.can_approve_sessions'):
            return True
        if letter.status == 'Client_Pending' and user.has_perm('accounts.can_approve_client'):
            return True
        return False

    def get_approval_type(self, letter):
        """Determine which approval type is needed based on letter status"""
        user = self.request.user

        if letter.status == 'Radius_Pending' and user.has_perm('accounts.can_approve_radius'):
            return 'radius'
        elif letter.status == 'Sessions_Pending' and user.has_perm('accounts.can_approve_sessions'):
            return 'sessions'
        elif letter.status == 'Client_Pending' and user.has_perm('accounts.can_approve_client'):
            return 'client'
        return None


class FACSLetterDetailView(LetterDetailView):
    """FACS letter detail view"""
    template_name = 'letters/facs_detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(FACSLetters, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        letter = self.object

        # FIX: Ensure letter is in context
        context['letter'] = letter
        context['object'] = letter

        # Get client approval matrix
        context['client_approvals'] = letter.get_client_approval_matrix()
        context['approval_percentage'] = letter.get_approval_percentage()
        context['pending_clients'] = letter.get_pending_clients()

        return context


class ArtivaLetterDetailView(LetterDetailView):
    """Artiva letter detail view"""
    template_name = 'letters/artiva_detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(ArtivaLetters, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        letter = self.object

        # FIX: Ensure letter is in context
        context['letter'] = letter
        context['object'] = letter

        return context


class LetterEditView(LoginRequiredMixin, UpdateView):
    """Edit any letter (FACS or Artiva)"""

    # Remove fixed template_name - will be dynamic based on letter type

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')

        try:
            return FACSLetters.objects.get(pk=pk)
        except FACSLetters.DoesNotExist:
            try:
                return ArtivaLetters.objects.get(pk=pk)
            except ArtivaLetters.DoesNotExist:
                raise Http404("No letter found with this ID.")

    def get_template_names(self):
        """Return different template based on letter type"""
        if isinstance(self.object, FACSLetters):
            print(f"DEBUG: Loading FACS template for letter {self.object.letter_code}")
            return ['letters/edit_facs.html']
        else:
            print(f"DEBUG: Loading Artiva template for letter {self.object.letter_code}")
            return ['letters/edit_artiva.html']

    def get_form_class(self):
        if isinstance(self.object, FACSLetters):
            return FACSCreationForm
        else:
            return ArtivaCreationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        letter = self.object

        # Add letter to context
        context['letter'] = letter

        # Get CCO and Representative users
        from apps.accounts.models import User
        context['cco_users'] = User.objects.filter(
            role__in=['CCO', 'Representative'],
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        # Get Radius Approval data
        content_type = ContentType.objects.get_for_model(letter)
        try:
            radius_approval = RadiusApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['radius_approval'] = radius_approval
            context['radius_approval_date'] = radius_approval.approval_date.strftime(
                '%Y-%m-%d') if radius_approval.approval_date else ''
            context['approval_comments'] = radius_approval.comments
        except RadiusApproval.DoesNotExist:
            context['radius_approval'] = None
            context['radius_approval_date'] = ''
            context['approval_comments'] = ''

        # Get Sessions Approval data
        try:
            sessions_approval = SessionsApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['sessions_approval'] = sessions_approval
            context['sessions_approval_date'] = sessions_approval.approval_date.strftime(
                '%Y-%m-%d') if sessions_approval.approval_date else ''
        except SessionsApproval.DoesNotExist:
            context['sessions_approval'] = None
            context['sessions_approval_date'] = ''

        # Get Ticket information
        try:
            ticket = Ticket.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['ticket'] = ticket
            context['ticket_number'] = ticket.ticket_number
            context['ticket_open_date'] = ticket.open_date.strftime('%Y-%m-%dT%H:%M') if ticket.open_date else ''
            context['ticket_completed_date'] = ticket.completed_date.strftime(
                '%Y-%m-%dT%H:%M') if ticket.completed_date else ''
            context['ticket_notes'] = ticket.notes
        except Ticket.DoesNotExist:
            context['ticket'] = None
            context['ticket_number'] = ''
            context['ticket_open_date'] = ''
            context['ticket_completed_date'] = ''
            context['ticket_notes'] = ''

        # Get Documents - Add document_type and description to each document
        documents = DocumentAttachment.objects.filter(
            content_type=content_type,
            object_id=letter.id
        ).order_by('-upload_date')

        # Enrich documents with display values
        for doc in documents:
            doc.display_type = doc.get_document_type_display()
        context['documents'] = documents

        # Get Versions
        context['versions'] = LetterVersion.objects.filter(
            content_type=content_type,
            object_id=letter.id
        ).order_by('-version_number')

        # Format client approvals for FACS template
        if letter.system_type == 'FACS' and hasattr(letter, 'client_approvals') and letter.client_approvals:
            # Create a dictionary with normalized keys for template use
            normalized_approvals = {}

            # Map display names to template-safe keys
            client_key_map = {
                'US Bank': 'US_Bank',
                'US Bank Retail': 'US_Bank_Retail',
                'Discover': 'Discover',
                'Wells Fargo': 'Wells_Fargo',
                'Capital One': 'Capital_One',
            }

            for client_name, approval_data in letter.client_approvals.items():
                # Get the template-safe key
                safe_key = client_key_map.get(client_name)
                if safe_key:
                    normalized_approvals[safe_key] = {
                        'status': approval_data.get('status', 'Pending'),
                        'contact': approval_data.get('contact', ''),
                        'date': approval_data.get('date'),
                        'comments': approval_data.get('comments', '')
                    }
                else:
                    # Handle custom client names
                    custom_key = client_name.replace(' ', '_')
                    normalized_approvals[custom_key] = {
                        'status': approval_data.get('status', 'Pending'),
                        'contact': approval_data.get('contact', ''),
                        'date': approval_data.get('date'),
                        'comments': approval_data.get('comments', ''),
                        'custom_name': approval_data.get('custom_name', client_name)
                    }

            context['client_approvals'] = normalized_approvals

        return context

    def get_success_url(self):
        """Redirect to the correct detail page based on letter type"""
        if self.object.system_type == 'FACS':
            return reverse('letters:facs_detail', kwargs={'pk': self.object.id})
        else:
            return reverse('letters:artiva_detail', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        letter = self.object

        # Save the form data first
        response = super().form_valid(form)

        # ========== UPDATE CLIENT APPROVALS (FACS only) ==========
        if letter.system_type == 'FACS':
            client_approvals = {}

            # Define clients with their template field names
            clients = [
                ('US Bank', 'client_us_bank', 'client_contact_us_bank'),
                ('US Bank Retail', 'client_us_bank_retail', 'client_contact_us_bank_retail'),
                ('Discover', 'client_discover', 'client_contact_discover'),
                ('Wells Fargo', 'client_wells_fargo', 'client_contact_wells_fargo'),
                ('Capital One', 'client_capital_one', 'client_contact_capital_one'),
            ]

            for client_name, checkbox_field, contact_field in clients:
                if self.request.POST.get(checkbox_field):
                    contact = self.request.POST.get(contact_field, '')
                    client_approvals[client_name] = {
                        'status': 'Pending',
                        'date': None,
                        'contact': contact,
                        'comments': ''
                    }

            # Handle custom client if exists
            if self.request.POST.get('client_custom'):
                custom_name = self.request.POST.get('client_custom_name', '')
                custom_contact = self.request.POST.get('client_contact_custom', '')
                if custom_name:
                    client_approvals[custom_name] = {
                        'status': 'Pending',
                        'date': None,
                        'contact': custom_contact,
                        'comments': '',
                        'custom_name': custom_name
                    }

            # Update letter's client approvals
            if client_approvals:
                letter.client_approvals = client_approvals
            elif letter.client_approvals:
                # If no clients selected but there were existing, clear them
                letter.client_approvals = {}
            letter.save()

        # ========== UPDATE TICKET INFORMATION ==========
        ticket_number = self.request.POST.get('ticket_number')
        ticket_open_date = self.request.POST.get('ticket_open_date')
        ticket_completed_date = self.request.POST.get('ticket_completed_date')
        ticket_notes = self.request.POST.get('ticket_notes', '')

        content_type = ContentType.objects.get_for_model(letter)

        if ticket_number or ticket_open_date:
            ticket, created = Ticket.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={
                    'ticket_number': ticket_number or f"TKT-{letter.id}",
                    'status': 'Open',
                    'notes': ticket_notes
                }
            )

            if not created:
                if ticket_number:
                    ticket.ticket_number = ticket_number
                if ticket_open_date:
                    try:
                        ticket.open_date = timezone.make_aware(
                            datetime.strptime(ticket_open_date, '%Y-%m-%dT%H:%M')
                        )
                    except (ValueError, TypeError):
                        pass
                if ticket_completed_date:
                    try:
                        ticket.completed_date = timezone.make_aware(
                            datetime.strptime(ticket_completed_date, '%Y-%m-%dT%H:%M')
                        )
                    except (ValueError, TypeError):
                        pass
                ticket.notes = ticket_notes
                ticket.save()
        else:
            # If no ticket info provided, delete existing ticket if any
            Ticket.objects.filter(content_type=content_type, object_id=letter.id).delete()

        # ========== HANDLE NEW DOCUMENT UPLOAD ==========
        if self.request.FILES.get('document'):
            doc_file = self.request.FILES['document']
            document_type = self.request.POST.get('document_type', 'Original')
            document_description = self.request.POST.get('document_description', '')

            DocumentAttachment.objects.create(
                content_type=content_type,
                object_id=letter.id,
                file=doc_file,
                file_name=doc_file.name,
                file_type=doc_file.name.split('.')[-1].lower(),
                document_type=document_type,
                description=document_description,
                uploaded_by=self.request.user,
                is_current=True
            )
            messages.success(self.request, f'Document "{doc_file.name}" uploaded successfully!')

        # ========== UPDATE APPROVAL DATES (CCO ONLY) ==========
        if self.request.user.role == 'CCO':
            radius_approval_date = self.request.POST.get('radius_approval_date')
            cco_representative_id = self.request.POST.get('cco_representative')
            approval_comments = self.request.POST.get('approval_comments', '')

            # Update Radius Approval
            if cco_representative_id or radius_approval_date:
                radius_approval, created = RadiusApproval.objects.get_or_create(
                    content_type=content_type,
                    object_id=letter.id
                )
                if cco_representative_id:
                    radius_approval.cco_or_representative_id = cco_representative_id
                if radius_approval_date:
                    try:
                        radius_approval.approval_date = timezone.make_aware(
                            datetime.combine(
                                datetime.strptime(radius_approval_date, '%Y-%m-%d').date(),
                                datetime.min.time()
                            )
                        )
                        radius_approval.approval_status = 'Approved'
                    except (ValueError, TypeError):
                        pass
                else:
                    radius_approval.approval_status = 'Pending'
                    radius_approval.approval_date = None
                radius_approval.comments = approval_comments
                radius_approval.save()

            # Update Sessions Approval
            sessions_approval_date = self.request.POST.get('sessions_approval_date')
            if sessions_approval_date:
                sessions_approval, created = SessionsApproval.objects.get_or_create(
                    content_type=content_type,
                    object_id=letter.id
                )
                try:
                    sessions_approval.approval_date = timezone.make_aware(
                        datetime.combine(
                            datetime.strptime(sessions_approval_date, '%Y-%m-%d').date(),
                            datetime.min.time()
                        )
                    )
                    sessions_approval.approval_status = 'Approved'
                    sessions_approval.comments = approval_comments
                    sessions_approval.save()
                except (ValueError, TypeError):
                    pass

        # ========== UPDATE LETTER STATUS BASED ON ACTION ==========
        action = self.request.POST.get('action')

        if action == 'submit' and letter.status == 'Draft':
            # Submit for review
            letter.status = 'Radius_Pending'
            letter.submitted_at = timezone.now()
            letter.save()

            # Create approval records if they don't exist
            RadiusApproval.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={'approval_status': 'Pending', 'comments': ''}
            )
            SessionsApproval.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={'approval_status': 'Pending', 'comments': ''}
            )

            # Notify CCO users
            from apps.accounts.models import Notification
            cco_users = User.objects.filter(role='CCO')
            for cco in cco_users:
                Notification.objects.create(
                    user=cco,
                    type='approval_needed',
                    title='New Letter Submitted',
                    message=f'Letter {letter.letter_code} has been submitted for approval.',
                    link=reverse('letters:detail', args=[letter.id])
                )

            messages.success(self.request, f'Letter {letter.letter_code} submitted for review!')
        elif action == 'draft':
            if letter.status == 'Draft':
                messages.success(self.request, 'Letter saved as draft.')
            else:
                messages.info(self.request, 'Letter updated but not resubmitted for review.')
        else:
            messages.success(self.request, 'Letter updated successfully!')

        return response

    def form_invalid(self, form):
        """Handle invalid form submission"""
        # Print errors for debugging
        print("Form errors:", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")

        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class FACSEditView(LoginRequiredMixin, UpdateView):
    """Edit FACS letter"""
    model = FACSLetters
    form_class = FACSCreationForm
    template_name = 'letters/edit_facs.html'

    def get_object(self, queryset=None):
        return get_object_or_404(FACSLetters, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        letter = self.object

        # Debug - print to terminal
        print(f"=== FACSEditView DEBUG ===")
        print(f"letter.id: {letter.id}")
        print(f"letter.letter_code: {letter.letter_code}")
        print(f"type(letter.id): {type(letter.id)}")

        # Add letter to context
        context['letter'] = letter
        context['system_type'] = 'FACS'

        # Get CCO and Representative users
        from apps.accounts.models import User
        context['cco_users'] = User.objects.filter(
            role__in=['CCO', 'Representative'],
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        # Get Radius Approval data
        content_type = ContentType.objects.get_for_model(letter)
        try:
            radius_approval = RadiusApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['radius_approval'] = radius_approval
            context['radius_approval_date'] = radius_approval.approval_date.strftime(
                '%Y-%m-%d') if radius_approval.approval_date else ''
            context['approval_comments'] = radius_approval.comments
        except RadiusApproval.DoesNotExist:
            context['radius_approval'] = None
            context['radius_approval_date'] = ''
            context['approval_comments'] = ''

        # Get Sessions Approval data
        try:
            sessions_approval = SessionsApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['sessions_approval'] = sessions_approval
            context['sessions_approval_date'] = sessions_approval.approval_date.strftime(
                '%Y-%m-%d') if sessions_approval.approval_date else ''
        except SessionsApproval.DoesNotExist:
            context['sessions_approval'] = None
            context['sessions_approval_date'] = ''

        # Get Ticket information
        try:
            ticket = Ticket.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['ticket'] = ticket
            context['ticket_number'] = ticket.ticket_number
            context['ticket_open_date'] = ticket.open_date.strftime('%Y-%m-%dT%H:%M') if ticket.open_date else ''
            context['ticket_completed_date'] = ticket.completed_date.strftime(
                '%Y-%m-%dT%H:%M') if ticket.completed_date else ''
            context['ticket_notes'] = ticket.notes
        except Ticket.DoesNotExist:
            context['ticket'] = None
            context['ticket_number'] = ''
            context['ticket_open_date'] = ''
            context['ticket_completed_date'] = ''
            context['ticket_notes'] = ''

        # Get Documents
        documents = DocumentAttachment.objects.filter(
            content_type=content_type,
            object_id=letter.id
        ).order_by('-upload_date')

        for doc in documents:
            doc.display_type = doc.get_document_type_display()
        context['documents'] = documents

        # Get Versions
        context['versions'] = LetterVersion.objects.filter(
            content_type=content_type,
            object_id=letter.id
        ).order_by('-version_number')

        # Format client approvals for FACS template
        if hasattr(letter, 'client_approvals') and letter.client_approvals:
            normalized_approvals = {}
            client_key_map = {
                'US Bank': 'US_Bank',
                'US Bank Retail': 'US_Bank_Retail',
                'Discover': 'Discover',
                'Wells Fargo': 'Wells_Fargo',
                'Capital One': 'Capital_One',
            }

            for client_name, approval_data in letter.client_approvals.items():
                safe_key = client_key_map.get(client_name)
                if safe_key:
                    normalized_approvals[safe_key] = {
                        'status': approval_data.get('status', 'Pending'),
                        'date': approval_data.get('date'),
                        'comments': approval_data.get('comments', '')
                    }
                else:

                    pass

            context['client_approvals'] = normalized_approvals
            print(
                f"DEBUG: Only showing {len(normalized_approvals)} selected clients: {list(normalized_approvals.keys())}")
        else:
            context['client_approvals'] = {}

        return context

    def get_success_url(self):
        return reverse('letters:facs_detail', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        letter = self.object

        # ========== FIX: Manually set communication_code from hidden field ==========
        communication_code = self.request.POST.get('communication_code')
        if communication_code:
            letter.communication_code = communication_code
            print(f"DEBUG FACSEditView: Set communication_code to '{communication_code}'")
            # Save immediately to ensure it's not lost
            letter.save(update_fields=['communication_code'])

        # Save the form data first
        response = super().form_valid(form)

        # Refresh to get updated values
        letter.refresh_from_db()

        # Double-check communication_code is still there
        if not letter.communication_code and communication_code:
            letter.communication_code = communication_code
            letter.save(update_fields=['communication_code'])
            print(f"DEBUG FACSEditView: Re-saved communication_code = '{communication_code}'")

        # ========== UPDATE CLIENT APPROVALS ==========
        client_approvals = {}

        clients = [
            ('US Bank', 'client_us_bank'),
            ('US Bank Retail', 'client_us_bank_retail'),
            ('Discover', 'client_discover'),
            ('Wells Fargo', 'client_wells_fargo'),
            ('Capital One', 'client_capital_one'),
        ]

        for client_name, checkbox_field in clients:
            if self.request.POST.get(checkbox_field):
                client_approvals[client_name] = {
                    'status': 'Pending',
                    'date': None,
                    'contact': '',
                    'comments': ''
                }

        if client_approvals:
            letter.client_approvals = client_approvals
        elif letter.client_approvals:
            letter.client_approvals = {}
        letter.save()

        # ========== UPDATE TICKET INFORMATION ==========
        ticket_number = self.request.POST.get('ticket_number')
        ticket_open_date = self.request.POST.get('ticket_open_date')
        ticket_completed_date = self.request.POST.get('ticket_completed_date')
        ticket_notes = self.request.POST.get('ticket_notes', '')

        content_type = ContentType.objects.get_for_model(letter)

        # Convert open_date from form input
        open_date = None
        if ticket_open_date:
            try:
                open_date = timezone.make_aware(datetime.strptime(ticket_open_date, '%Y-%m-%dT%H:%M'))
            except (ValueError, TypeError):
                open_date = timezone.now()
        else:
            open_date = timezone.now()  # Default to now if not provided

        if ticket_number or ticket_open_date:
            ticket, created = Ticket.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={
                    'ticket_number': ticket_number or f"TKT-{letter.id}",
                    'open_date': open_date,  # ADD THIS
                    'status': 'Open',
                    'notes': ticket_notes
                }
            )

            if not created:
                if ticket_number:
                    ticket.ticket_number = ticket_number
                if ticket_open_date:
                    try:
                        ticket.open_date = timezone.make_aware(
                            datetime.strptime(ticket_open_date, '%Y-%m-%dT%H:%M')
                        )
                    except (ValueError, TypeError):
                        pass
                if ticket_completed_date:
                    try:
                        ticket.completed_date = timezone.make_aware(
                            datetime.strptime(ticket_completed_date, '%Y-%m-%dT%H:%M')
                        )
                    except (ValueError, TypeError):
                        pass
                ticket.notes = ticket_notes
                ticket.save()
        else:
            # If no ticket info provided, delete existing ticket
            Ticket.objects.filter(content_type=content_type, object_id=letter.id).delete()

        # ========== HANDLE NEW DOCUMENT UPLOAD ==========
        if self.request.FILES.get('document'):
            doc_file = self.request.FILES['document']
            document_type = self.request.POST.get('document_type', 'Original')
            document_description = self.request.POST.get('document_description', '')

            DocumentAttachment.objects.create(
                content_type=content_type,
                object_id=letter.id,
                file=doc_file,
                file_name=doc_file.name,
                file_type=doc_file.name.split('.')[-1].lower(),
                document_type=document_type,
                description=document_description,
                uploaded_by=self.request.user,
                is_current=True
            )
            messages.success(self.request, f'Document "{doc_file.name}" uploaded successfully!')

        # ========== UPDATE APPROVAL DATES (CCO ONLY) ==========
        if self.request.user.role == 'CCO':
            radius_approval_date = self.request.POST.get('radius_approval_date')
            cco_representative_id = self.request.POST.get('cco_representative')
            approval_comments = self.request.POST.get('approval_comments', '')

            if cco_representative_id or radius_approval_date:
                radius_approval, created = RadiusApproval.objects.get_or_create(
                    content_type=content_type,
                    object_id=letter.id
                )
                if cco_representative_id:
                    radius_approval.cco_or_representative_id = cco_representative_id
                if radius_approval_date:
                    try:
                        radius_approval.approval_date = timezone.make_aware(
                            datetime.combine(
                                datetime.strptime(radius_approval_date, '%Y-%m-%d').date(),
                                datetime.min.time()
                            )
                        )
                        radius_approval.approval_status = 'Approved'
                    except (ValueError, TypeError):
                        pass
                else:
                    radius_approval.approval_status = 'Pending'
                    radius_approval.approval_date = None
                radius_approval.comments = approval_comments
                radius_approval.save()

            sessions_approval_date = self.request.POST.get('sessions_approval_date')
            if sessions_approval_date:
                sessions_approval, created = SessionsApproval.objects.get_or_create(
                    content_type=content_type,
                    object_id=letter.id
                )
                try:
                    sessions_approval.approval_date = timezone.make_aware(
                        datetime.combine(
                            datetime.strptime(sessions_approval_date, '%Y-%m-%d').date(),
                            datetime.min.time()
                        )
                    )
                    sessions_approval.approval_status = 'Approved'
                    sessions_approval.comments = approval_comments
                    sessions_approval.save()
                except (ValueError, TypeError):
                    pass

        # ========== UPDATE LETTER STATUS BASED ON ACTION ==========
        action = self.request.POST.get('action')

        if action == 'submit' and letter.status == 'Draft':
            letter.status = 'Radius_Pending'
            letter.submitted_at = timezone.now()
            letter.save()

            RadiusApproval.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={'approval_status': 'Pending', 'comments': ''}
            )
            SessionsApproval.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={'approval_status': 'Pending', 'comments': ''}
            )

            from apps.accounts.models import Notification
            cco_users = User.objects.filter(role='CCO')
            for cco in cco_users:
                Notification.objects.create(
                    user=cco,
                    type='approval_needed',
                    title='New Letter Submitted',
                    message=f'Letter {letter.letter_code} has been submitted for approval.',
                    link=reverse('letters:facs_detail', args=[letter.id])
                )

            messages.success(self.request, f'Letter {letter.letter_code} submitted for review!')
        elif action == 'draft':
            if letter.status == 'Draft':
                messages.success(self.request, 'Letter saved as draft.')
            else:
                messages.info(self.request, 'Letter updated but not resubmitted for review.')
        else:
            messages.success(self.request, 'Letter updated successfully!')

        return response

    def form_invalid(self, form):
        print("Form errors:", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ArtivaEditView(LoginRequiredMixin, UpdateView):
    """Edit Artiva letter"""
    model = ArtivaLetters
    form_class = ArtivaCreationForm
    template_name = 'letters/edit_artiva.html'

    def get_object(self, queryset=None):
        return get_object_or_404(ArtivaLetters, pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        letter = self.object

        # Add letter to context
        context['letter'] = letter
        context['system_type'] = 'ARTIVA'

        # Get CCO and Representative users
        from apps.accounts.models import User
        context['cco_users'] = User.objects.filter(
            role__in=['CCO', 'Representative'],
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        # Get Radius Approval data
        content_type = ContentType.objects.get_for_model(letter)
        try:
            radius_approval = RadiusApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['radius_approval'] = radius_approval
            context['radius_approval_date'] = radius_approval.approval_date.strftime(
                '%Y-%m-%d') if radius_approval.approval_date else ''
            context['approval_comments'] = radius_approval.comments
        except RadiusApproval.DoesNotExist:
            context['radius_approval'] = None
            context['radius_approval_date'] = ''
            context['approval_comments'] = ''

        # Get Sessions Approval data
        try:
            sessions_approval = SessionsApproval.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['sessions_approval'] = sessions_approval
            context['sessions_approval_date'] = sessions_approval.approval_date.strftime(
                '%Y-%m-%d') if sessions_approval.approval_date else ''
        except SessionsApproval.DoesNotExist:
            context['sessions_approval'] = None
            context['sessions_approval_date'] = ''

        # Get Ticket information from separate Ticket model
        try:
            ticket = Ticket.objects.get(
                content_type=content_type,
                object_id=letter.id
            )
            context['ticket'] = ticket
            context['ticket_number'] = ticket.ticket_number
            context['ticket_open_date'] = ticket.open_date.strftime('%Y-%m-%dT%H:%M') if ticket.open_date else ''
            context['ticket_completed_date'] = ticket.completed_date.strftime(
                '%Y-%m-%dT%H:%M') if ticket.completed_date else ''
            context['ticket_notes'] = ticket.notes
        except Ticket.DoesNotExist:
            context['ticket'] = None
            context['ticket_number'] = ''
            context['ticket_open_date'] = ''
            context['ticket_completed_date'] = ''
            context['ticket_notes'] = ''

        # Get Documents
        documents = DocumentAttachment.objects.filter(
            content_type=content_type,
            object_id=letter.id
        ).order_by('-upload_date')

        for doc in documents:
            doc.display_type = doc.get_document_type_display()
        context['documents'] = documents

        # Get Versions
        context['versions'] = LetterVersion.objects.filter(
            content_type=content_type,
            object_id=letter.id
        ).order_by('-version_number')

        return context

    def get_success_url(self):
        return reverse('letters:artiva_detail', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        letter = self.object

        # Get the action from the form submission
        action = self.request.POST.get('action')
        print(f"DEBUG ArtivaEditView: Action = '{action}'")
        print(f"DEBUG ArtivaEditView: Letter status before = '{letter.status}'")
        print(f"DEBUG ArtivaEditView: communication_code from POST = '{self.request.POST.get('communication_code')}'")
        print(f"DEBUG ArtivaEditView: letter.communication_code before = '{letter.communication_code}'")

        # FIX: Manually set communication_code from hidden field
        communication_code = self.request.POST.get('communication_code')
        if communication_code:
            letter.communication_code = communication_code
            print(f"DEBUG: Set communication_code to '{communication_code}'")

        # Save the letter first to ensure communication_code is saved
        letter.save(update_fields=['communication_code'])

        # Save the form data first (this saves other fields)
        response = super().form_valid(form)

        # Refresh letter object after save
        letter.refresh_from_db()
        print(f"DEBUG: After refresh, communication_code = '{letter.communication_code}'")

        # Double-check communication_code is still there
        if not letter.communication_code and communication_code:
            letter.communication_code = communication_code
            letter.save(update_fields=['communication_code'])
            print(f"DEBUG: Re-saved communication_code = '{letter.communication_code}'")

        # ========== UPDATE TICKET INFORMATION ==========
        ticket_number = self.request.POST.get('ticket_number')
        ticket_open_date = self.request.POST.get('ticket_open_date')
        ticket_completed_date = self.request.POST.get('ticket_completed_date')
        ticket_notes = self.request.POST.get('ticket_notes', '')

        content_type = ContentType.objects.get_for_model(letter)

        # Convert open_date from form input
        open_date = None
        if ticket_open_date:
            try:
                open_date = timezone.make_aware(datetime.strptime(ticket_open_date, '%Y-%m-%dT%H:%M'))
            except (ValueError, TypeError):
                open_date = timezone.now()
        else:
            open_date = timezone.now()  # Default to now if not provided

        if ticket_number or ticket_open_date:
            ticket, created = Ticket.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={
                    'ticket_number': ticket_number or f"TKT-{letter.id}",
                    'open_date': open_date,  # ADD THIS
                    'status': 'Open',
                    'notes': ticket_notes
                }
            )

            if not created:
                if ticket_number:
                    ticket.ticket_number = ticket_number
                if ticket_open_date:
                    try:
                        ticket.open_date = timezone.make_aware(
                            datetime.strptime(ticket_open_date, '%Y-%m-%dT%H:%M')
                        )
                    except (ValueError, TypeError):
                        pass
                if ticket_completed_date:
                    try:
                        ticket.completed_date = timezone.make_aware(
                            datetime.strptime(ticket_completed_date, '%Y-%m-%dT%H:%M')
                        )
                    except (ValueError, TypeError):
                        pass
                ticket.notes = ticket_notes
                ticket.save()
        else:
            # If no ticket info provided, delete existing ticket
            Ticket.objects.filter(content_type=content_type, object_id=letter.id).delete()

        # ========== HANDLE NEW DOCUMENT UPLOAD ==========
        if self.request.FILES.get('document'):
            doc_file = self.request.FILES['document']
            document_type = self.request.POST.get('document_type', 'Original')
            document_description = self.request.POST.get('document_description', '')

            DocumentAttachment.objects.create(
                content_type=content_type,
                object_id=letter.id,
                file=doc_file,
                file_name=doc_file.name,
                file_type=doc_file.name.split('.')[-1].lower(),
                document_type=document_type,
                description=document_description,
                uploaded_by=self.request.user,
                is_current=True
            )
            messages.success(self.request, f'Document "{doc_file.name}" uploaded successfully!')

        # ========== UPDATE APPROVAL DATES (CCO ONLY) ==========
        if self.request.user.role == 'CCO':
            radius_approval_date = self.request.POST.get('radius_approval_date')
            cco_representative_id = self.request.POST.get('cco_representative')
            approval_comments = self.request.POST.get('approval_comments', '')

            if cco_representative_id or radius_approval_date:
                radius_approval, created = RadiusApproval.objects.get_or_create(
                    content_type=content_type,
                    object_id=letter.id
                )
                if cco_representative_id:
                    radius_approval.cco_or_representative_id = cco_representative_id
                if radius_approval_date:
                    try:
                        radius_approval.approval_date = timezone.make_aware(
                            datetime.combine(
                                datetime.strptime(radius_approval_date, '%Y-%m-%d').date(),
                                datetime.min.time()
                            )
                        )
                        radius_approval.approval_status = 'Approved'
                    except (ValueError, TypeError):
                        pass
                else:
                    radius_approval.approval_status = 'Pending'
                    radius_approval.approval_date = None
                radius_approval.comments = approval_comments
                radius_approval.save()

            sessions_approval_date = self.request.POST.get('sessions_approval_date')
            if sessions_approval_date:
                sessions_approval, created = SessionsApproval.objects.get_or_create(
                    content_type=content_type,
                    object_id=letter.id
                )
                try:
                    sessions_approval.approval_date = timezone.make_aware(
                        datetime.combine(
                            datetime.strptime(sessions_approval_date, '%Y-%m-%d').date(),
                            datetime.min.time()
                        )
                    )
                    sessions_approval.approval_status = 'Approved'
                    sessions_approval.comments = approval_comments
                    sessions_approval.save()
                except (ValueError, TypeError):
                    pass

        # ========== UPDATE LETTER STATUS BASED ON ACTION ==========
        if action == 'submit' and letter.status == 'Draft':
            letter.status = 'Radius_Pending'
            letter.submitted_at = timezone.now()
            letter.save()
            print(f"DEBUG: Letter status changed to '{letter.status}'")

            RadiusApproval.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={'approval_status': 'Pending', 'comments': ''}
            )
            SessionsApproval.objects.get_or_create(
                content_type=content_type,
                object_id=letter.id,
                defaults={'approval_status': 'Pending', 'comments': ''}
            )

            from apps.accounts.models import Notification
            cco_users = User.objects.filter(role='CCO')
            for cco in cco_users:
                Notification.objects.create(
                    user=cco,
                    type='approval_needed',
                    title='New Letter Submitted',
                    message=f'Letter {letter.letter_code} has been submitted for approval.',
                    link=reverse('letters:artiva_detail', args=[letter.id])
                )

            messages.success(self.request, f'Artiva letter {letter.letter_code} submitted for review!')

        elif action == 'draft':
            if letter.status == 'Draft':
                messages.success(self.request, 'Letter saved as draft.')
            else:
                messages.info(self.request, 'Letter updated successfully.')
        else:
            messages.success(self.request, 'Letter updated successfully!')

        return response

    def form_invalid(self, form):
        print("Form errors:", form.errors)
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


@login_required
def submit_for_review(request, pk):
    """Submit letter for review"""
    from django.contrib.contenttypes.models import ContentType
    from apps.accounts.models import User, Notification

    # IMPORTANT: Try to determine letter type from the request path first
    # This is the most reliable method
    referer = request.META.get('HTTP_REFERER', '')
    path = request.path

    print(f"=== DEBUG submit_for_review ===")
    print(f"PK: {pk}")
    print(f"Path: {path}")
    print(f"Referer: {referer}")

    # Method 1: Check if the request came from Artiva create page
    is_artiva = False
    if 'create_artiva' in referer or 'artiva' in path:
        is_artiva = True
        print("Detected Artiva letter from referer/path")

    # Try to find the letter based on detection
    letter = None
    is_facs = False

    if is_artiva:
        try:
            letter = ArtivaLetters.objects.get(pk=pk)
            is_facs = False
            print(f"Found ARTIVA letter: {letter.letter_code} (ID: {letter.id})")
        except ArtivaLetters.DoesNotExist:
            pass

    # If not found by detection, try Artiva first (since Artiva was causing issues)
    if not letter:
        try:
            letter = ArtivaLetters.objects.get(pk=pk)
            is_facs = False
            print(f"Found ARTIVA letter (fallback): {letter.letter_code} (ID: {letter.id})")
        except ArtivaLetters.DoesNotExist:
            try:
                letter = FACSLetters.objects.get(pk=pk)
                is_facs = True
                print(f"Found FACS letter: {letter.letter_code} (ID: {letter.id})")
            except FACSLetters.DoesNotExist:
                messages.error(request, 'Letter not found.')
                return redirect('letters:list')

    letter_type = "FACS" if is_facs else "ARTIVA"

    # Check if letter can be submitted (Draft or Internal_Work)
    if letter.status not in ['Draft', 'Internal_Work']:
        messages.warning(request,
                         f'{letter_type} letter {letter.letter_code} has already been submitted (Status: {letter.status}).')
        if is_facs:
            return redirect('letters:facs_detail', pk=letter.id)
        else:
            return redirect('letters:artiva_detail', pk=letter.id)

    content_type = ContentType.objects.get_for_model(letter)

    # Check if approval records already exist
    radius_exists = RadiusApproval.objects.filter(content_type=content_type, object_id=letter.id).exists()
    sessions_exists = SessionsApproval.objects.filter(content_type=content_type, object_id=letter.id).exists()

    # Handle existing approval records
    if radius_exists and sessions_exists:
        radius_approval = RadiusApproval.objects.get(content_type=content_type, object_id=letter.id)
        sessions_approval = SessionsApproval.objects.get(content_type=content_type, object_id=letter.id)

        radius_approved = radius_approval.approval_status == 'Approved'
        sessions_approved = sessions_approval.approval_status == 'Approved'

        if radius_approved and sessions_approved:
            letter.status = 'Client_Pending' if is_facs else 'CCO_Review'
        elif radius_approved:
            letter.status = 'Sessions_Pending'
        elif sessions_approved:
            letter.status = 'Radius_Pending'
        else:
            letter.status = 'Radius_Pending'

        letter.submitted_at = timezone.now()
        letter.save()

        messages.success(request, f'{letter_type} letter {letter.letter_code} submitted for review!')

        if is_facs:
            return redirect('letters:facs_detail', pk=letter.id)
        else:
            return redirect('letters:artiva_detail', pk=letter.id)

    # Create missing approval records
    if not radius_exists:
        RadiusApproval.objects.create(
            content_type=content_type,
            object_id=letter.id,
            approval_status='Pending',
            comments=''
        )

    if not sessions_exists:
        SessionsApproval.objects.create(
            content_type=content_type,
            object_id=letter.id,
            approval_status='Pending',
            comments=''
        )

    # Update status
    letter.status = 'Radius_Pending'
    letter.submitted_at = timezone.now()
    letter.save()

    # Create notification for CCO
    cco_users = User.objects.filter(role='CCO')
    for cco in cco_users:
        if is_facs:
            link = reverse('letters:facs_detail', args=[letter.id])
        else:
            link = reverse('letters:artiva_detail', args=[letter.id])
        Notification.objects.create(
            user=cco,
            type='approval_needed',
            title='New Letter Submitted',
            message=f'{letter_type} letter {letter.letter_code} has been submitted for approval.',
            link=link
        )

    messages.success(request, f'{letter_type} letter {letter.letter_code} submitted for review!')

    if is_facs:
        return redirect('letters:facs_detail', pk=letter.id)
    else:
        return redirect('letters:artiva_detail', pk=letter.id)


class PendingApprovalsView(LoginRequiredMixin, TemplateView):
    """View pending approvals"""
    template_name = 'letters/pending_approvals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['radius_pending'] = []
        context['sessions_pending'] = []
        context['client_pending'] = []
        context['cco_pending'] = []

        if user.role == 'CCO':
            # Get all letters pending CCO approval
            facs_pending = FACSLetters.objects.filter(status='CCO_Review')
            artiva_pending = ArtivaLetters.objects.filter(status='CCO_Review')
            context['cco_pending'] = list(facs_pending) + list(artiva_pending)

            # FIX: Also show client approvals to CCO
            client_pending_letters = FACSLetters.objects.filter(status='Client_Pending')
            for letter in client_pending_letters:
                context['client_pending'].append(letter)

        if user.role in ['CCO', 'Representative', 'InternalReviewer']:
            # Get radius approvals pending
            radius_pending = RadiusApproval.objects.filter(
                approval_status='Pending'
            )
            for radius in radius_pending:
                if radius.letter:
                    context['radius_pending'].append({
                        'letter': radius.letter,
                        'approval': radius
                    })

            # Get sessions approvals pending
            sessions_pending = SessionsApproval.objects.filter(
                approval_status='Pending'
            )
            for session in sessions_pending:
                if session.letter:
                    context['sessions_pending'].append({
                        'letter': session.letter,
                        'approval': session
                    })

        if user.role == 'ClientManager':
            # Get client approvals pending
            facs_pending = FACSLetters.objects.filter(status='Client_Pending')
            for letter in facs_pending:
                context['client_pending'].append(letter)

        return context


class RadiusPendingView(LoginRequiredMixin, ListView):
    """View radius pending approvals"""
    template_name = 'letters/radius_pending.html'
    context_object_name = 'pending_approvals'

    def get_queryset(self):
        return RadiusApproval.objects.filter(
            approval_status='Pending'
        ).select_related('cco_or_representative')


class SessionsPendingView(LoginRequiredMixin, ListView):
    """View sessions pending approvals"""
    template_name = 'letters/sessions_pending.html'
    context_object_name = 'pending_approvals'

    def get_queryset(self):
        return SessionsApproval.objects.filter(
            approval_status='Pending'
        )


class ClientPendingView(LoginRequiredMixin, ListView):
    """View client pending approvals"""
    template_name = 'letters/client_pending.html'
    context_object_name = 'pending_letters'

    def get_queryset(self):
        return FACSLetters.objects.filter(status='Client_Pending')


@login_required
def radius_approve(request, pk):
    """Approve radius request"""
    radius_approval = get_object_or_404(RadiusApproval, pk=pk)
    letter = radius_approval.letter

    if request.method == 'POST':
        action = request.POST.get('action')
        comments = request.POST.get('comments', '')

        if action == 'approve':
            radius_approval.approve(request.user, comments)
            messages.success(request, f'Radius approval for {letter.letter_code} approved.')
        else:
            radius_approval.reject(request.user, comments)
            messages.warning(request, f'Radius approval for {letter.letter_code} rejected.')

        # Log activity - FIX THIS SECTION
        try:
            UserActivityLog.log_activity(
                user=request.user,  # Make sure this is not None
                action='approve' if action == 'approve' else 'reject',
                model_name='RadiusApproval',
                object_id=radius_approval.id,
                object_repr=str(radius_approval),
                changes={'comments': comments}
            )
        except Exception as e:
            print(f"Error logging activity: {e}")

        return redirect('letters:pending_approvals')

    return render(request, 'letters/radius_approve.html', {
        'radius_approval': radius_approval,
        'letter': letter
    })


@login_required
def sessions_approve(request, pk):
    """Approve sessions request"""
    sessions_approval = get_object_or_404(SessionsApproval, pk=pk)
    letter = sessions_approval.letter

    if request.method == 'POST':
        action = request.POST.get('action')
        session_reference = request.POST.get('session_reference', '')
        comments = request.POST.get('comments', '')

        if action == 'approve':
            sessions_approval.approve(session_reference, comments)
            messages.success(request, f'Sessions approval for {letter.letter_code} approved.')
        else:
            sessions_approval.reject(comments)
            messages.warning(request, f'Sessions approval for {letter.letter_code} rejected.')

        # Log activity - FIX THIS SECTION
        try:
            UserActivityLog.log_activity(
                user=request.user,  # Make sure this is not None
                action='approve' if action == 'approve' else 'reject',
                model_name='SessionsApproval',
                object_id=sessions_approval.id,
                object_repr=str(sessions_approval),
                changes={'session_reference': session_reference, 'comments': comments}
            )
        except Exception as e:
            print(f"Error logging activity: {e}")

        return redirect('letters:pending_approvals')

    return render(request, 'letters/sessions_approve.html', {
        'sessions_approval': sessions_approval,
        'letter': letter
    })


@login_required
def client_approve(request, pk):
    """Client approval page - allows selecting and approving individual clients"""
    letter = get_object_or_404(FACSLetters, pk=pk)

    # Check permission - only ClientManager or CCO can approve
    if request.user.role not in ['ClientManager', 'CCO']:
        messages.error(request, 'You do not have permission to approve clients.')
        return redirect('letters:facs_detail', pk=letter.id)

    # Get client approval data
    client_approvals = letter.get_client_approval_matrix()
    approval_percentage = letter.get_approval_percentage()
    pending_clients = letter.get_pending_clients()

    # Handle POST request (form submission)
    if request.method == 'POST':
        client_name = request.POST.get('client_name')
        comments = request.POST.get('comments', '')

        if client_name:
            if letter.update_client_approval(client_name, 'Approved', comments=comments):
                messages.success(request, f'Client "{client_name}" has been approved.')

                # Check if all clients are approved
                if letter.all_clients_approved():
                    letter.status = 'CCO_Review'
                    letter.save()
                    messages.info(request, 'All clients approved! Letter moved to CCO review.')

                return redirect('letters:pending_approvals')
            else:
                messages.error(request, f'Failed to approve client "{client_name}".')
        else:
            messages.error(request, 'Please select a client to approve.')

        return redirect('letters:client_approve', pk=letter.id)

    # Handle GET request - show the approval form
    context = {
        'letter': letter,
        'client_approvals': client_approvals,
        'approval_percentage': approval_percentage,
        'pending_clients': pending_clients,
    }
    return render(request, 'letters/client_approve.html', context)


@login_required
def cco_final_approve(request, pk):
    """Final CCO approval"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        comments = request.POST.get('comments', '')

        if action == 'approve':
            letter.status = 'Completed'
            letter.completed_at = timezone.now()
            letter.save()

            # Create final version
            version_data = {
                'letter_code': letter.letter_code,
                'document_description': letter.document_description,
                'letter_description': letter.letter_description,
                'approved_by': request.user.username,
                'approval_date': timezone.now().isoformat()
            }

            LetterVersion.objects.create(
                content_type=ContentType.objects.get_for_model(letter),
                object_id=letter.id,
                version_number=letter.current_version,
                version_author=request.user,
                version_note='Final approved version',
                version_data=version_data,
                revision_reason='Final approval'
            )

            messages.success(request, f'Letter {letter.letter_code} approved and completed!')
        else:
            letter.status = 'Rejected'
            letter.save()
            messages.warning(request, f'Letter {letter.letter_code} returned for revision.')

        # Log activity - FIX THIS SECTION
        try:
            UserActivityLog.log_activity(
                user=request.user,  # Make sure this is not None
                action='approve' if action == 'approve' else 'reject',
                model_name=letter.__class__.__name__,
                object_id=letter.id,
                object_repr=letter.letter_code,
                changes={'comments': comments}
            )
        except Exception as e:
            print(f"Error logging activity: {e}")

        # Create notification
        Notification.objects.create(
            user=letter.created_by,
            type='approval_completed' if action == 'approve' else 'revision_needed',
            title=f'Letter {letter.letter_code} - {action.title()}d',
            message=f'Your letter has been {action}d. Comments: {comments}',
            link=reverse('letters:detail', args=[letter.id])
        )

        return redirect('letters:list')

    return render(request, 'letters/cco_approve.html', {
        'letter': letter
    })


class ReportsView(LoginRequiredMixin, TemplateView):
    """Advanced reports and analytics view"""
    template_name = 'letters/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range from request or default to last 30 days
        start_date = self.request.GET.get('start')
        end_date = self.request.GET.get('end')

        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)

        context['start_date'] = start_date
        context['end_date'] = end_date

        # Get content types for FACS and Artiva
        facs_ct = ContentType.objects.get_for_model(FACSLetters)
        artiva_ct = ContentType.objects.get_for_model(ArtivaLetters)

        # Filter letters by date range
        facs_letters = FACSLetters.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        artiva_letters = ArtivaLetters.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        all_letters = list(facs_letters) + list(artiva_letters)

        # Get IDs for filtering approvals
        facs_ids = list(facs_letters.values_list('id', flat=True))
        artiva_ids = list(artiva_letters.values_list('id', flat=True))

        # Total counts
        total_facs = facs_letters.count()
        total_artiva = artiva_letters.count()
        total_letters = total_facs + total_artiva

        # Previous period for comparison
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date - timedelta(days=1)
        prev_facs = FACSLetters.objects.filter(created_at__date__gte=prev_start, created_at__date__lte=prev_end).count()
        prev_artiva = ArtivaLetters.objects.filter(created_at__date__gte=prev_start,
                                                   created_at__date__lte=prev_end).count()
        previous_total_letters = prev_facs + prev_artiva

        # Calculate growth rate
        if previous_total_letters > 0:
            growth_rate = ((total_letters - previous_total_letters) / previous_total_letters) * 100
        else:
            growth_rate = 100 if total_letters > 0 else 0

        # Completion rates
        completed_facs = facs_letters.filter(status='Completed').count()
        completed_artiva = artiva_letters.filter(status='Completed').count()
        completed_count = completed_facs + completed_artiva
        completion_rate = (completed_count / total_letters * 100) if total_letters > 0 else 0

        # Previous completion rate
        prev_completed_facs = FACSLetters.objects.filter(status='Completed', created_at__date__gte=prev_start,
                                                         created_at__date__lte=prev_end).count()
        prev_completed_artiva = ArtivaLetters.objects.filter(status='Completed', created_at__date__gte=prev_start,
                                                             created_at__date__lte=prev_end).count()
        prev_completed = prev_completed_facs + prev_completed_artiva
        prev_total = prev_facs + prev_artiva
        previous_completion_rate = (prev_completed / prev_total * 100) if prev_total > 0 else 0

        completion_growth = completion_rate - previous_completion_rate

        # Average processing time (days from creation to completion)
        completed_letters = []
        for letter in facs_letters.filter(status='Completed', completed_at__isnull=False):
            if letter.completed_at and letter.created_at:
                days = (letter.completed_at - letter.created_at).days
                completed_letters.append(days)
        for letter in artiva_letters.filter(status='Completed', completed_at__isnull=False):
            if letter.completed_at and letter.created_at:
                days = (letter.completed_at - letter.created_at).days
                completed_letters.append(days)

        avg_processing_days = sum(completed_letters) / len(completed_letters) if completed_letters else 0

        # Previous processing time
        prev_completed_letters = []
        prev_facs_completed = FACSLetters.objects.filter(status='Completed', completed_at__date__gte=prev_start,
                                                         completed_at__date__lte=prev_end)
        prev_artiva_completed = ArtivaLetters.objects.filter(status='Completed', completed_at__date__gte=prev_start,
                                                             completed_at__date__lte=prev_end)

        for letter in prev_facs_completed:
            if letter.completed_at and letter.created_at:
                days = (letter.completed_at - letter.created_at).days
                prev_completed_letters.append(days)
        for letter in prev_artiva_completed:
            if letter.completed_at and letter.created_at:
                days = (letter.completed_at - letter.created_at).days
                prev_completed_letters.append(days)

        previous_avg_days = sum(prev_completed_letters) / len(prev_completed_letters) if prev_completed_letters else 0
        processing_improvement = (
                    (previous_avg_days - avg_processing_days) / previous_avg_days * 100) if previous_avg_days > 0 else 0

        # Active users count
        active_users = UserActivityLog.objects.filter(timestamp__date__gte=start_date).values('user').distinct().count()
        prev_active_users = UserActivityLog.objects.filter(timestamp__date__gte=prev_start,
                                                           timestamp__date__lte=prev_end).values(
            'user').distinct().count()
        user_growth = ((active_users - prev_active_users) / prev_active_users * 100) if prev_active_users > 0 else 0

        # Status counts
        draft_count = facs_letters.filter(status='Draft').count() + artiva_letters.filter(status='Draft').count()
        radius_pending = facs_letters.filter(status='Radius_Pending').count() + artiva_letters.filter(
            status='Radius_Pending').count()
        sessions_pending = facs_letters.filter(status='Sessions_Pending').count() + artiva_letters.filter(
            status='Sessions_Pending').count()
        client_pending = facs_letters.filter(status='Client_Pending').count()
        cco_pending = facs_letters.filter(status='CCO_Review').count() + artiva_letters.filter(
            status='CCO_Review').count()

        # Monthly trend (last 12 months)
        months = []
        facs_trend = []
        artiva_trend = []
        for i in range(11, -1, -1):
            month_date = timezone.now() - timedelta(days=30 * i)
            month_name = month_date.strftime('%b %Y')
            months.append(month_name)
            facs_count = FACSLetters.objects.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month
            ).count()
            artiva_count = ArtivaLetters.objects.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month
            ).count()
            facs_trend.append(facs_count)
            artiva_trend.append(artiva_count)

        # Weekly trend (last 8 weeks)
        weekly_labels = []
        weekly_data = []
        for i in range(7, -1, -1):
            week_start = timezone.now() - timedelta(days=7 * i)
            week_end = week_start + timedelta(days=6)
            week_count = FACSLetters.objects.filter(created_at__date__gte=week_start,
                                                    created_at__date__lte=week_end).count() + \
                         ArtivaLetters.objects.filter(created_at__date__gte=week_start,
                                                      created_at__date__lte=week_end).count()
            weekly_labels.append(f"Week {8 - i}")
            weekly_data.append(week_count)

        # System averages
        facs_avg_days = 0
        artiva_avg_days = 0
        facs_completed_list = []
        for letter in facs_letters.filter(status='Completed', completed_at__isnull=False):
            if letter.completed_at and letter.created_at:
                facs_completed_list.append((letter.completed_at - letter.created_at).days)
        artiva_completed_list = []
        for letter in artiva_letters.filter(status='Completed', completed_at__isnull=False):
            if letter.completed_at and letter.created_at:
                artiva_completed_list.append((letter.completed_at - letter.created_at).days)

        facs_avg_days = sum(facs_completed_list) / len(facs_completed_list) if facs_completed_list else 0
        artiva_avg_days = sum(artiva_completed_list) / len(artiva_completed_list) if artiva_completed_list else 0

        # Top performers - Use correct related names
        top_performers = User.objects.annotate(
            letter_count=Count('facsletters_created_letters') + Count('artivaletters_created_letters')
        ).order_by('-letter_count')[:5]
        top_performers_labels = [u.get_full_name() or u.username for u in top_performers]
        top_performers_data = [u.letter_count for u in top_performers]

        # Funnel data - FIXED: Use content type filters for GenericForeignKey
        radius_approved_facs = RadiusApproval.objects.filter(
            content_type=facs_ct,
            object_id__in=facs_ids,
            approval_status='Approved'
        ).count()
        radius_approved_artiva = RadiusApproval.objects.filter(
            content_type=artiva_ct,
            object_id__in=artiva_ids,
            approval_status='Approved'
        ).count()
        radius_approved = radius_approved_facs + radius_approved_artiva

        sessions_approved_facs = SessionsApproval.objects.filter(
            content_type=facs_ct,
            object_id__in=facs_ids,
            approval_status='Approved'
        ).count()
        sessions_approved_artiva = SessionsApproval.objects.filter(
            content_type=artiva_ct,
            object_id__in=artiva_ids,
            approval_status='Approved'
        ).count()
        sessions_approved = sessions_approved_facs + sessions_approved_artiva

        funnel_data = [
            total_letters,
            radius_approved,
            sessions_approved,
            client_pending,
            cco_pending,
            completed_count
        ]

        # Approval times by stage - FIXED: Use content type filters
        radius_approvals_facs = RadiusApproval.objects.filter(
            content_type=facs_ct,
            object_id__in=facs_ids,
            approval_status='Approved',
            approval_date__isnull=False,
            created_at__isnull=False
        )
        radius_approvals_artiva = RadiusApproval.objects.filter(
            content_type=artiva_ct,
            object_id__in=artiva_ids,
            approval_status='Approved',
            approval_date__isnull=False,
            created_at__isnull=False
        )

        sessions_approvals_facs = SessionsApproval.objects.filter(
            content_type=facs_ct,
            object_id__in=facs_ids,
            approval_status='Approved',
            approval_date__isnull=False,
            created_at__isnull=False
        )
        sessions_approvals_artiva = SessionsApproval.objects.filter(
            content_type=artiva_ct,
            object_id__in=artiva_ids,
            approval_status='Approved',
            approval_date__isnull=False,
            created_at__isnull=False
        )

        radius_times = []
        for ra in radius_approvals_facs:
            if ra.created_at and ra.approval_date:
                hours = (ra.approval_date - ra.created_at).total_seconds() / 3600
                radius_times.append(hours)
        for ra in radius_approvals_artiva:
            if ra.created_at and ra.approval_date:
                hours = (ra.approval_date - ra.created_at).total_seconds() / 3600
                radius_times.append(hours)

        sessions_times = []
        for sa in sessions_approvals_facs:
            if sa.created_at and sa.approval_date:
                hours = (sa.approval_date - sa.created_at).total_seconds() / 3600
                sessions_times.append(hours)
        for sa in sessions_approvals_artiva:
            if sa.created_at and sa.approval_date:
                hours = (sa.approval_date - sa.created_at).total_seconds() / 3600
                sessions_times.append(hours)

        approval_times = [
            sum(radius_times) / len(radius_times) if radius_times else 0,
            sum(sessions_times) / len(sessions_times) if sessions_times else 0,
            48,  # Client approval average (placeholder)
            24  # CCO final average (placeholder)
        ]

        # Client approval data
        client_labels = ['US Bank', 'US Bank Retail', 'Discover', 'Wells Fargo', 'Capital One']
        client_approved = []
        client_pending_data = []

        # Get real client approval data from FACS letters
        for client in client_labels:
            approved_count = 0
            pending_count = 0
            for letter in facs_letters:
                approvals = letter.get_client_approval_matrix()
                if client in approvals:
                    if approvals[client].get('status') == 'Approved':
                        approved_count += 1
                    else:
                        pending_count += 1
            client_approved.append(approved_count)
            client_pending_data.append(pending_count)

        # Top users - Use correct related names
        top_users = User.objects.annotate(
            letter_count=Count('facsletters_created_letters') + Count('artivaletters_created_letters')
        ).order_by('-letter_count')[:5]
        top_users_labels = [u.get_full_name() or u.username for u in top_users]
        top_users_data = [u.letter_count for u in top_users]

        # User trend (last 30 days)
        user_trend_labels = []
        user_trend_data = []
        for i in range(29, -1, -1):
            day = timezone.now() - timedelta(days=i)
            user_trend_labels.append(day.strftime('%b %d'))
            active_count = UserActivityLog.objects.filter(timestamp__date=day).values('user').distinct().count()
            user_trend_data.append(active_count)

        # Role distribution
        role_labels = ['CCO', 'Representative', 'Reviewer', 'Client Manager', 'Viewer']
        role_data = [
            User.objects.filter(role='CCO').count(),
            User.objects.filter(role='Representative').count(),
            User.objects.filter(role='InternalReviewer').count(),
            User.objects.filter(role='ClientManager').count(),
            User.objects.filter(role='Viewer').count()
        ]

        # Targets
        target_letters = int(total_letters * 1.1) if total_letters > 0 else 10

        # Insights data
        peak_day = "Wednesday"
        peak_hour = "10 AM - 2 PM"
        fast_approval_percentage = 45
        us_bank_approval_rate = round((client_approved[0] / (client_approved[0] + client_pending_data[0]) * 100) if (
                                                                                                                                client_approved[
                                                                                                                                    0] +
                                                                                                                                client_pending_data[
                                                                                                                                    0]) > 0 else 0,
                                      1)
        capital_one_avg_days = 4.5

        context.update({
            'total_letters': total_letters,
            'total_facs': total_facs,
            'total_artiva': total_artiva,
            'growth_rate': round(growth_rate, 1),
            'completion_rate': round(completion_rate, 1),
            'completion_growth': round(completion_growth, 1),
            'avg_processing_days': round(avg_processing_days, 1),
            'processing_improvement': round(processing_improvement, 1),
            'active_users': active_users,
            'user_growth': round(user_growth, 1),
            'draft_count': draft_count,
            'radius_pending': radius_pending,
            'sessions_pending': sessions_pending,
            'client_pending': client_pending,
            'cco_pending': cco_pending,
            'completed_count': completed_count,
            'previous_total_letters': previous_total_letters,
            'previous_completion_rate': round(previous_completion_rate, 1),
            'previous_avg_days': round(previous_avg_days, 1),
            'target_letters': target_letters,
            'facs_completed': completed_facs,
            'artiva_completed': completed_artiva,
            'facs_avg_days': round(facs_avg_days, 1),
            'artiva_avg_days': round(artiva_avg_days, 1),
            'monthly_labels': months,
            'facs_trend': facs_trend,
            'artiva_trend': artiva_trend,
            'weekly_labels': weekly_labels,
            'weekly_data': weekly_data,
            'top_performers_labels': top_performers_labels,
            'top_performers_data': top_performers_data,
            'funnel_data': funnel_data,
            'approval_times': [round(t, 1) for t in approval_times],
            'client_labels': client_labels,
            'client_approved': client_approved,
            'client_pending_data': client_pending_data,
            'top_users_labels': top_users_labels,
            'top_users_data': top_users_data,
            'user_trend_labels': user_trend_labels,
            'user_trend_data': user_trend_data,
            'role_labels': role_labels,
            'role_data': role_data,
            'peak_day': peak_day,
            'peak_hour': peak_hour,
            'fast_approval_percentage': fast_approval_percentage,
            'us_bank_approval_rate': us_bank_approval_rate,
            'capital_one_avg_days': capital_one_avg_days,
        })

        return context


class CompletedLettersView(LoginRequiredMixin, ListView):
    """View completed letters"""
    template_name = 'letters/completed.html'
    context_object_name = 'letters'
    paginate_by = 25

    def get_queryset(self):
        facs_completed = FACSLetters.objects.filter(status='Completed')
        artiva_completed = ArtivaLetters.objects.filter(status='Completed')

        all_completed = list(facs_completed) + list(artiva_completed)
        all_completed.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)

        return all_completed


class DelegatedLettersView(LoginRequiredMixin, ListView):
    """View delegated letters"""
    template_name = 'letters/delegated.html'
    context_object_name = 'letters'

    def get_queryset(self):
        facs_delegated = FACSLetters.objects.filter(delegated_to=self.request.user)
        artiva_delegated = ArtivaLetters.objects.filter(delegated_to=self.request.user)

        all_delegated = list(facs_delegated) + list(artiva_delegated)
        all_delegated.sort(key=lambda x: x.created_at, reverse=True)

        return all_delegated


class AuditLogView(LoginRequiredMixin, ListView):
    """View audit logs"""
    template_name = 'letters/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        from apps.common.models import AuditLog
        return AuditLog.objects.all().select_related('user').order_by('-timestamp')


# Additional helper functions
@login_required
def version_history(request, pk):
    """View version history"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    versions = LetterVersion.objects.filter(
        content_type=ContentType.objects.get_for_model(letter),
        object_id=letter.id
    ).order_by('-version_number')

    return render(request, 'letters/version_history.html', {
        'letter': letter,
        'versions': versions
    })


@login_required
def download_version(request, pk, version):
    """Download a specific version"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    letter_version = get_object_or_404(LetterVersion,
                                       content_type=ContentType.objects.get_for_model(letter),
                                       object_id=letter.id,
                                       version_number=version
                                       )

    if letter_version.pdf_copy:
        return redirect(letter_version.pdf_copy.url)
    else:
        messages.error(request, 'No PDF available for this version.')
        return redirect('letters:detail', pk=letter.id)


@login_required
def compare_versions(request, pk):
    """Compare two versions"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    version1_id = request.GET.get('version1')
    version2_id = request.GET.get('version2')

    version1 = get_object_or_404(LetterVersion, pk=version1_id) if version1_id else None
    version2 = get_object_or_404(LetterVersion, pk=version2_id) if version2_id else None

    return render(request, 'letters/compare_versions.html', {
        'letter': letter,
        'version1': version1,
        'version2': version2
    })


@login_required
def create_new_version(request, pk):
    """Create a new version"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    if request.method == 'POST':
        form = LetterVersionForm(request.POST, request.FILES)
        if form.is_valid():
            version_data = {
                'letter_code': letter.letter_code,
                'document_description': letter.document_description,
                'letter_description': letter.letter_description,
                'created_by': request.user.username,
                'created_at': timezone.now().isoformat(),
                'changes': form.cleaned_data['version_note']
            }

            # Get current version number
            current_version_num = int(letter.current_version.replace('V.', ''))
            new_version_num = current_version_num + 1
            new_version = f"V.{new_version_num}"

            version = LetterVersion.objects.create(
                content_type=ContentType.objects.get_for_model(letter),
                object_id=letter.id,
                version_number=new_version,
                version_author=request.user,
                version_note=form.cleaned_data['version_note'],
                version_data=version_data,
                revision_reason=form.cleaned_data['revision_reason'],
                pdf_copy=form.cleaned_data['pdf_copy']
            )

            # Update letter's current version
            letter.current_version = new_version
            letter.save()

            messages.success(request, f'New version {new_version} created successfully!')
            return redirect('letters:detail', pk=letter.id)
    else:
        form = LetterVersionForm()

    return render(request, 'letters/create_version.html', {
        'letter': letter,
        'form': form
    })


@login_required
def upload_document(request, pk):
    """Upload document for letter"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.content_type = ContentType.objects.get_for_model(letter)
            doc.object_id = letter.id
            doc.letter = letter
            doc.uploaded_by = request.user
            doc.file = request.FILES['file']
            doc.save()

            messages.success(request, 'Document uploaded successfully!')
            return redirect('letters:detail', pk=letter.id)
    else:
        form = DocumentUploadForm()

    return render(request, 'letters/upload_document.html', {
        'letter': letter,
        'form': form
    })


@login_required
def download_document(request, doc_id):
    """Download document"""
    doc = get_object_or_404(DocumentAttachment, pk=doc_id)
    doc.increment_download_count()
    return redirect(doc.file.url)


@login_required
def delete_document(request, doc_id):
    """Delete document"""
    doc = get_object_or_404(DocumentAttachment, pk=doc_id)
    letter_id = doc.object_id
    doc.delete()
    messages.success(request, 'Document deleted successfully!')
    return redirect('letters:detail', pk=letter_id)


@login_required
def document_list(request, pk):
    """List documents for a letter"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    documents = DocumentAttachment.objects.filter(
        content_type=ContentType.objects.get_for_model(letter),
        object_id=letter.id
    )

    return render(request, 'letters/documents.html', {
        'letter': letter,
        'documents': documents
    })


@login_required
def create_ticket(request, pk):
    """Create a ticket for a letter"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.content_type = ContentType.objects.get_for_model(letter)
            ticket.object_id = letter.id
            ticket.letter = letter
            ticket.save()

            messages.success(request, f'Ticket {ticket.ticket_number} created successfully!')
            return redirect('letters:detail', pk=letter.id)
    else:
        form = TicketForm()

    return render(request, 'letters/create_ticket.html', {
        'letter': letter,
        'form': form
    })


@login_required
def ticket_detail(request, pk):
    """View ticket details"""
    ticket = get_object_or_404(Ticket, pk=pk)
    return render(request, 'letters/ticket_detail.html', {'ticket': ticket})


@login_required
def update_ticket(request, ticket_id):
    """Update ticket"""
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ticket updated successfully!')
            return redirect('letters:ticket_detail', pk=ticket.id)
    else:
        form = TicketForm(instance=ticket)

    return render(request, 'letters/update_ticket.html', {
        'ticket': ticket,
        'form': form
    })


@login_required
def generate_report(request):
    """Generate a report"""
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            report_type = form.cleaned_data['report_type']

            # Generate report based on type
            if report_type == 'summary':
                facs_count = FACSLetters.objects.filter(
                    created_at__date__range=[start_date, end_date]
                ).count()
                artiva_count = ArtivaLetters.objects.filter(
                    created_at__date__range=[start_date, end_date]
                ).count()

                context = {
                    'report_type': 'Summary Report',
                    'start_date': start_date,
                    'end_date': end_date,
                    'facs_count': facs_count,
                    'artiva_count': artiva_count,
                    'total_count': facs_count + artiva_count,
                }
                return render(request, 'letters/report_summary.html', context)

            elif report_type == 'approval':
                radius_approved = RadiusApproval.objects.filter(
                    approval_date__date__range=[start_date, end_date],
                    approval_status='Approved'
                ).count()
                sessions_approved = SessionsApproval.objects.filter(
                    approval_date__date__range=[start_date, end_date],
                    approval_status='Approved'
                ).count()

                context = {
                    'report_type': 'Approval Report',
                    'start_date': start_date,
                    'end_date': end_date,
                    'radius_approved': radius_approved,
                    'sessions_approved': sessions_approved,
                }
                return render(request, 'letters/report_approval.html', context)

    return redirect('letters:reports')


@login_required
def export_data(request):
    """Export data to CSV/Excel"""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="letters_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Letter Code', 'Type', 'Status', 'Created By', 'Created At', 'Completed At'])

    facs_letters = FACSLetters.objects.all()
    artiva_letters = ArtivaLetters.objects.all()

    for letter in facs_letters:
        writer.writerow([
            letter.letter_code,
            'FACS',
            letter.status,
            letter.created_by.username,
            letter.created_at,
            letter.completed_at or ''
        ])

    for letter in artiva_letters:
        writer.writerow([
            letter.letter_code,
            'Artiva',
            letter.status,
            letter.created_by.username,
            letter.created_at,
            letter.completed_at or ''
        ])

    return response


@login_required
def update_letter_status(request, pk):
    """Update letter status"""
    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(letter.STATUS_CHOICES):
            letter.status = new_status
            letter.save()
            messages.success(request, f'Letter status updated to {new_status}')

    return redirect('letters:detail', pk=letter.id)


@login_required
def bulk_approve(request):
    """Bulk approve letters (CCO only)"""
    if request.user.role != 'CCO':
        messages.error(request, 'Only CCO can perform bulk approvals.')
        return redirect('letters:list')

    if request.method == 'POST':
        form = BulkApprovalForm(request.POST)
        if form.is_valid():
            letters = form.cleaned_data['letters']
            comments = form.cleaned_data['comments']
            action = form.cleaned_data.get('approval_action', 'approve')

            for letter in letters:
                if action == 'approve':
                    letter.status = 'Completed'
                    letter.completed_at = timezone.now()
                    letter.save()

                    # Create final version
                    version_data = {
                        'letter_code': letter.letter_code,
                        'bulk_approved': True,
                        'approved_by': request.user.username,
                        'approval_date': timezone.now().isoformat()
                    }

                    LetterVersion.objects.create(
                        content_type=ContentType.objects.get_for_model(letter),
                        object_id=letter.id,
                        version_number=letter.current_version,
                        version_author=request.user,
                        version_note=f'Bulk approved: {comments}',
                        version_data=version_data,
                        revision_reason='Bulk approval'
                    )

                    # Create notification
                    Notification.objects.create(
                        user=letter.created_by,
                        type='approval_completed',
                        title=f'Letter {letter.letter_code} Approved',
                        message=f'Your letter has been bulk approved. Comments: {comments}',
                        link=reverse('letters:detail', args=[letter.id])
                    )

            messages.success(request, f'{letters.count()} letters have been {action}d.')
            return redirect('letters:list')

    return redirect('letters:list')


@login_required
def bulk_delete(request):
    """Bulk delete letters (CCO only)"""
    if request.user.role != 'CCO':
        messages.error(request, 'Only CCO can perform bulk deletions.')
        return redirect('letters:list')

    if request.method == 'POST':
        letter_ids = request.POST.getlist('letter_ids')
        count = 0

        for letter_id in letter_ids:
            try:
                letter = FACSLetters.objects.get(pk=letter_id)
                letter.delete()
                count += 1
            except FACSLetters.DoesNotExist:
                try:
                    letter = ArtivaLetters.objects.get(pk=letter_id)
                    letter.delete()
                    count += 1
                except ArtivaLetters.DoesNotExist:
                    pass

        messages.success(request, f'{count} letters have been deleted.')

    return redirect('letters:list')


@login_required
def cco_approval_management(request, pk):
    """CCO approval management page to set Radius and Sessions approval dates"""
    if request.user.role != 'CCO':
        messages.error(request, 'Only CCO can access this page.')
        return redirect('letters:detail', pk=pk)

    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    # Get or create approval records
    radius_approval, _ = RadiusApproval.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(letter),
        object_id=letter.id
    )
    sessions_approval, _ = SessionsApproval.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(letter),
        object_id=letter.id
    )

    # Get CCO and Representative users
    from apps.accounts.models import User
    cco_users = User.objects.filter(
        role__in=['CCO', 'Representative'],
        is_active=True
    ).order_by('first_name', 'last_name', 'username')

    return render(request, 'letters/cco_approval_management.html', {
        'letter': letter,
        'radius_approval': radius_approval,
        'sessions_approval': sessions_approval,
        'cco_users': cco_users
    })


@login_required
def update_radius_approval(request, pk):
    """Update Radius approval (CCO only)"""
    if request.user.role != 'CCO':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    if request.method == 'POST':
        radius_approval, _ = RadiusApproval.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(letter),
            object_id=letter.id
        )

        # Update fields
        cco_representative_id = request.POST.get('cco_representative')
        if cco_representative_id:
            radius_approval.cco_or_representative_id = cco_representative_id

        approval_date = request.POST.get('radius_approval_date')
        if approval_date:
            radius_approval.approval_date = datetime.strptime(approval_date, '%Y-%m-%d').date()
            radius_approval.approval_status = 'Approved'
        else:
            radius_approval.approval_status = 'Pending'
            radius_approval.approval_date = None

        radius_approval.comments = request.POST.get('radius_comments', '')
        radius_approval.save()

        # Update letter status if needed
        if radius_approval.approval_status == 'Approved':
            # Check if sessions is also approved
            sessions_approval = SessionsApproval.objects.filter(
                content_type=ContentType.objects.get_for_model(letter),
                object_id=letter.id
            ).first()

            if sessions_approval and sessions_approval.approval_status == 'Approved':
                if letter.system_type == 'FACS':
                    letter.status = 'Client_Pending'
                else:
                    letter.status = 'CCO_Review'
            else:
                letter.status = 'Sessions_Pending'
            letter.save()

        messages.success(request, 'Radius approval updated successfully!')

    return redirect('letters:cco_approval_management', pk=letter.id)


@login_required
def update_sessions_approval(request, pk):
    """Update Sessions approval (CCO only)"""
    if request.user.role != 'CCO':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        letter = FACSLetters.objects.get(pk=pk)
    except FACSLetters.DoesNotExist:
        letter = get_object_or_404(ArtivaLetters, pk=pk)

    if request.method == 'POST':
        sessions_approval, _ = SessionsApproval.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(letter),
            object_id=letter.id
        )

        # Update fields
        session_reference = request.POST.get('session_reference', '')
        if session_reference:
            sessions_approval.session_reference = session_reference

        approval_date = request.POST.get('sessions_approval_date')
        if approval_date:
            sessions_approval.approval_date = datetime.strptime(approval_date, '%Y-%m-%d').date()
            sessions_approval.approval_status = 'Approved'
        else:
            sessions_approval.approval_status = 'Pending'
            sessions_approval.approval_date = None

        sessions_approval.comments = request.POST.get('sessions_comments', '')
        sessions_approval.save()

        # Update letter status if needed
        if sessions_approval.approval_status == 'Approved':
            # Check if radius is also approved
            radius_approval = RadiusApproval.objects.filter(
                content_type=ContentType.objects.get_for_model(letter),
                object_id=letter.id
            ).first()

            if radius_approval and radius_approval.approval_status == 'Approved':
                if letter.system_type == 'FACS':
                    letter.status = 'Client_Pending'
                else:
                    letter.status = 'CCO_Review'
            else:
                letter.status = 'Radius_Pending'
            letter.save()

        messages.success(request, 'Sessions approval updated successfully!')

    return redirect('letters:cco_approval_management', pk=letter.id)


@login_required
def update_document(request, doc_id):
    """Update document metadata (type and description)"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            doc = get_object_or_404(DocumentAttachment, pk=doc_id)

            # Check permission - only document uploader or CCO can edit
            if request.user != doc.uploaded_by and request.user.role != 'CCO':
                return JsonResponse({'error': 'Permission denied'}, status=403)

            if 'document_type' in data:
                doc.document_type = data['document_type']
            if 'description' in data:
                doc.description = data['description']
            doc.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)