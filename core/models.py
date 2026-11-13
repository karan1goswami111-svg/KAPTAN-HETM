from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_identifier = models.CharField(max_length=100, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    auth_provider = models.CharField(max_length=20, default='native')  # 'native' or 'google'

    def __str__(self):
        return self.display_name or (self.user.username if self.user else "Guest")

class PersonalExpense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_identifier = models.CharField(max_length=100, null=True, blank=True)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100, default='Guest')
    month_year = models.CharField(max_length=7)  # Format: "YYYY-MM"
    monthly_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    dismiss_warning = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'guest_name', 'month_year')

    def __str__(self):
        owner = self.user.username if self.user else self.guest_name
        return f"{owner} - {self.month_year}: ₹{self.monthly_limit}"

class Group(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    members_list = models.TextField(help_text="Comma-separated list of member names")
    num_members = models.PositiveIntegerField(default=1)
    group_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_identifier = models.CharField(max_length=100, null=True, blank=True) # <--- Ye zaroori hai
    is_settled = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Expense(models.Model):
    group = models.ForeignKey(Group, related_name='expenses', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return f"{self.title} (₹{self.amount}) in {self.group.name}"

class ArchivedGroupHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_identifier = models.CharField(max_length=100, null=True, blank=True)
    group_name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    group_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    user_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    user_share = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    user_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    budget_breached = models.BooleanField(default=False)
    members_summary = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Archive: {self.group_name}"