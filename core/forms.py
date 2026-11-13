from django import forms
from .models import Group, Expense, Budget
from datetime import datetime

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description', 'group_budget', 'members_list']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Trip Name / Group Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description'}),
            'group_budget': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total Group Budget in ₹'}),
            'members_list': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Comma separated names e.g. Kaptan, Rahul, Priya'}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'amount', 'paid_by', 'date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expense Title (e.g., Dinner, Fuel)'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount in ₹'}),
            'paid_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Paid by member name'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class BudgetForm(forms.ModelForm):
    month_year = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'month', 'value': datetime.now().strftime('%Y-%m')}),
        label="Select Month & Year"
    )
    monthly_limit = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter monthly budget limit in ₹'}),
        label="Monthly Budget Limit (₹)"
    )

    class Meta:
        model = Budget
        fields = ['month_year', 'monthly_limit']