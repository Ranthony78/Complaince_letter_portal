# apps/documents/forms.py
from django import forms
from .models import Document, DocumentCategory


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'table_data': forms.Textarea(attrs={'rows': 10, 'class': 'json-editor'}),
            'view_permissions': forms.SelectMultiple(attrs={'class': 'select2-multiple'}),
        }

    def clean_table_data(self):
        data = self.cleaned_data.get('table_data')
        if data and isinstance(data, str):
            import json
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format")
        return data


class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = '__all__'