import csv
import random
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Group, Expense, Budget, UserProfile, PersonalExpense, ArchivedGroupHistory
from .forms import GroupForm, ExpenseForm, BudgetForm

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from dateutil.relativedelta import relativedelta

def login_view(request):
    if request.method == 'POST':
        if 'guest_login' in request.POST:
            # 1. Purane guest session ka saara data database se permanently wipe karo
            old_guest_id = request.session.get('guest_id')
            if old_guest_id:
                PersonalExpense.objects.filter(guest_identifier=old_guest_id).delete()
                Budget.objects.filter(guest_name="Guest", user=None).delete()
                ArchivedGroupHistory.objects.filter(guest_identifier=old_guest_id).delete()
                Group.objects.filter(created_by=None, guest_identifier=old_guest_id).delete()
            
            # 2. Session flush karke bilkul fresh naya guest ID generate karo
            request.session.flush()
            
            new_guest_id = 'guest_' + str(random.randint(100000, 999999))
            request.session['guest_id'] = new_guest_id
            request.session['display_name'] = 'Guest'
            request.session['is_guest_session'] = True
            request.session['trigger_welcome_modal'] = True
            
            UserProfile.objects.get_or_create(
                guest_identifier=new_guest_id,
                defaults={'display_name': 'Guest'}
            )
            return redirect('dashboard')
            
        userid_input = request.POST.get('userid')
        password_input = request.POST.get('password')
        
        if not userid_input or not password_input:
            messages.error(request, "Validation Error: Please fill in all mandatory fields!")
            return render(request, 'core/login.html')
            
        user = authenticate(request, username=userid_input, password=password_input)
        if user is not None:
            login(request, user)
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'display_name': user.username}
            )
            request.session['display_name'] = profile.display_name
            request.session.pop('is_guest_session', None)
            request.session.pop('guest_id', None)
            
            is_brand_new = request.session.pop('brand_new_user_' + str(user.id), False)
            request.session['is_new_user_login'] = is_brand_new
            request.session['trigger_welcome_modal'] = True
            return redirect('dashboard')
        else:
            messages.error(request, "Authentication Error: Invalid UserID or Password!")
            return render(request, 'core/login.html')
            
    return render(request, 'core/login.html')

def google_auth_callback_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if created or not profile.display_name:
        profile.auth_provider = 'google'
        profile.save()
        return redirect('set_google_name')
    
    request.session['display_name'] = profile.display_name
    request.session['trigger_welcome_modal'] = True
    return redirect('dashboard')

def set_google_name_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    if profile.display_name and profile.auth_provider == 'google':
        return redirect('dashboard')

    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        if not display_name:
            messages.error(request, "Validation Error: Please enter your personal name!")
            return render(request, 'core/Gset_name.html')
            
        profile.display_name = display_name
        profile.auth_provider = 'google'
        profile.save()
        
        request.session['display_name'] = display_name
        request.session['is_new_user_login'] = True
        request.session['trigger_welcome_modal'] = True
        messages.success(request, "Name successfully set! Welcome to KAPTAN-HETM.")
        return redirect('dashboard')
        
    return render(request, 'core/Gset_name.html')

def register_view(request):
    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        userid = request.POST.get('userid', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not display_name or not userid or not mobile or not password:
            messages.error(request, "Validation Error: All fields are required!")
            return render(request, 'core/register.html')

        if User.objects.filter(username=userid).exists():
            messages.error(request, "Validation Error: UserID already exists! Please choose another.")
            return render(request, 'core/register.html')

        if UserProfile.objects.filter(mobile_number=mobile).exists():
            messages.error(request, "Validation Error: This mobile number is already registered with another account!")
            return render(request, 'core/register.html')
            
        request.session['pending_reg'] = {
            'display_name': display_name,
            'userid': userid,
            'mobile': mobile,
            'password': password
        }
        
        otp = str(random.randint(100000, 999999))
        request.session['reg_otp'] = otp
        messages.success(request, f"OTP sent to mobile! (Demo OTP: {otp})")
        return redirect('verify_reg_otp')
        
    return render(request, 'core/register.html')

def verify_reg_otp_view(request):
    pending = request.session.get('pending_reg')
    correct_otp = request.session.get('reg_otp')
    
    if not pending or not correct_otp:
        return redirect('register')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        if entered_otp == correct_otp:
            display_name = pending['display_name']
            userid = pending['userid']
            mobile = pending['mobile']
            password = pending['password']
            
            user = User.objects.create_user(username=userid, password=password)
            UserProfile.objects.create(
                user=user, 
                display_name=display_name, 
                mobile_number=mobile, 
                is_phone_verified=True, 
                auth_provider='native'
            )
            
            request.session['brand_new_user_' + str(user.id)] = True
            request.session.pop('pending_reg', None)
            request.session.pop('reg_otp', None)
            
            messages.success(request, "Account successfully verified & created! Please login.")
            return redirect('login')
        else:
            messages.error(request, "Validation Error: Invalid OTP! Please enter the correct OTP.")
            
    return render(request, 'core/verify_reg_otp.html')

def forgot_password_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()
        if not mobile:
            messages.error(request, "Validation Error: Please enter your registered mobile number.")
            return render(request, 'core/forgot_password.html')

        profile = UserProfile.objects.filter(mobile_number=mobile).first()
        if profile and profile.user:
            otp = str(random.randint(100000, 999999))
            profile.otp_code = otp
            profile.save()
            request.session['reset_user_id'] = profile.user.id
            messages.success(request, f"OTP sent to mobile! (Demo OTP: {otp})")
            return redirect('verify_otp')
        else:
            messages.error(request, "Validation Error: This mobile number is not registered with any account!")
            return render(request, 'core/forgot_password.html')
            
    return render(request, 'core/forgot_password.html')

def verify_otp_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('forgot_password')
        
    user = get_object_or_404(User, id=user_id)
    profile = UserProfile.objects.filter(user=user).first()

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        if profile and profile.otp_code == entered_otp:
            request.session['otp_verified'] = True
            messages.success(request, f"OTP Verified! Your Username is: <strong>{user.username}</strong>. Now set your new password.")
            return redirect('reset_password')
        else:
            messages.error(request, "Validation Error: Invalid OTP! Please try again.")
    return render(request, 'core/verify_otp.html', {'username_hint': user.username})

def reset_password_view(request):
    if not request.session.get('otp_verified'):
        return redirect('forgot_password')
        
    user_id = request.session.get('reset_user_id')
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        p1 = request.POST.get('new_password', '').strip()
        p2 = request.POST.get('confirm_password', '').strip()

        if p1 == p2 and p1:
            user.set_password(p1)
            user.save()
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                profile.otp_code = None
                profile.save()
            request.session.pop('reset_user_id', None)
            request.session.pop('otp_verified', None)
            messages.success(request, "Password successfully reset! Please login with your new password.")
            return redirect('login')
        else:
            messages.error(request, "Validation Error: Passwords do not match or fields are empty!")
    return render(request, 'core/reset_password.html')

def profile_settings_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        new_mobile = request.POST.get('mobile_number', '').strip()
        new_password = request.POST.get('password', '').strip()

        if new_password:
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password successfully updated/created!")

        if new_mobile and new_mobile != (profile.mobile_number or ""):
            if UserProfile.objects.filter(mobile_number=new_mobile).exclude(user=user).exists():
                messages.error(request, "Validation Error: This mobile number is already used by another account!")
                return redirect('profile_settings')
            
            otp = str(random.randint(100000, 999999))
            profile.otp_code = otp
            profile.save()
            request.session['pending_mobile'] = new_mobile
            messages.success(request, f"OTP sent to new mobile number! (Demo OTP: {otp})")
            return redirect('verify_profile_otp')

        return redirect('profile_settings')

    display_name = profile.display_name or user.username
    email_id = user.email or "Google Authenticated User"
    mobile_number = profile.mobile_number or ""
    is_google_user = profile.auth_provider == 'google'

    context = {
        'display_name': display_name,
        'email_id': email_id,
        'mobile_number': mobile_number,
        'is_google_user': is_google_user,
    }
    return render(request, 'core/profile_settings.html', context)

def verify_profile_otp_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    pending_mobile = request.session.get('pending_mobile')

    if not pending_mobile:
        return redirect('profile_settings')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        if entered_otp == profile.otp_code:
            profile.mobile_number = pending_mobile
            profile.is_phone_verified = True
            profile.otp_code = None
            profile.save()
            
            request.session.pop('pending_mobile', None)
            messages.success(request, "Mobile number successfully verified and updated!")
            return redirect('profile_settings')
        else:
            messages.error(request, "Validation Error: Invalid OTP!")

    return render(request, 'core/verify_otp.html', {'username_hint': pending_mobile})

def logout_view(request):
    g_id = request.session.get('guest_id')
    if g_id:
        PersonalExpense.objects.filter(guest_identifier=g_id).delete()
        Budget.objects.filter(guest_name="Guest", user=None).delete()
        ArchivedGroupHistory.objects.filter(guest_identifier=g_id).delete()
        Group.objects.filter(created_by=None, guest_identifier=g_id).delete()
    
    logout(request)
    request.session.flush()
    messages.success(request, "Logged out successfully. All guest data has been purged.")
    return redirect('login')

def delete_account_view(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            request.user.delete()
        elif request.session.get('guest_id'):
            g_id = request.session.get('guest_id')
            PersonalExpense.objects.filter(guest_identifier=g_id).delete()
            Budget.objects.filter(guest_name="Guest", user=None).delete()
            ArchivedGroupHistory.objects.filter(guest_identifier=g_id).delete()
            Group.objects.filter(created_by=None, guest_identifier=g_id).delete()
        
        logout(request)
        request.session.flush()
        messages.success(request, "Account and all associated data permanently deleted.")
        return redirect('login')
    return redirect('dashboard')

def fresh_start_view(request):
    if request.user.is_authenticated:
        PersonalExpense.objects.filter(user=request.user).delete()
        Budget.objects.filter(user=request.user).delete()
        Group.objects.filter(created_by=request.user).delete()
        ArchivedGroupHistory.objects.filter(user=request.user).delete()
    elif request.session.get('guest_id'):
        g_id = request.session.get('guest_id')
        PersonalExpense.objects.filter(guest_identifier=g_id).delete()
        Budget.objects.filter(guest_name="Guest", user=None).delete()
        Group.objects.filter(created_by=None, guest_identifier=g_id).delete()
        ArchivedGroupHistory.objects.filter(guest_identifier=g_id).delete()
    
    messages.success(request, "Fresh Start executed! All ledger records, budgets and history archives have been erased.")
    return redirect('dashboard')

def add_personal_expense_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        amount = request.POST.get('amount', '').strip()
        date = request.POST.get('date', '').strip()
        
        if not title or not amount or not date:
            messages.error(request, "Validation Error: All fields are required to add a personal expense!")
            return redirect('dashboard')

        try:
            amt_val = float(amount)
            if amt_val <= 0:
                raise ValueError()
        except ValueError:
            messages.error(request, "Validation Error: Please enter a valid positive amount!")
            return redirect('dashboard')

        if request.user.is_authenticated:
            PersonalExpense.objects.create(user=request.user, title=title, amount=amt_val, date=date)
        elif request.session.get('guest_id'):
            g_id = request.session.get('guest_id')
            PersonalExpense.objects.create(guest_identifier=g_id, title=title, amount=amt_val, date=date)
        messages.success(request, "Standalone personal expense added successfully!")
    return redirect('dashboard')

def delete_personal_expense_view(request, exp_id):
    exp = get_object_or_404(PersonalExpense, id=exp_id)
    exp.delete()
    messages.success(request, "Personal expense deleted successfully!")
    return redirect('dashboard')

def dashboard_view(request):
    is_guest = request.session.get('is_guest_session', False)
    if not request.user.is_authenticated and not request.session.get('guest_id'):
        return redirect('login')

    user_obj = request.user if request.user.is_authenticated else None
    
    if user_obj:
        profile, _ = UserProfile.objects.get_or_create(user=user_obj)
        display_name = profile.display_name if profile.display_name else user_obj.username
        header_userid = user_obj.email if user_obj.email else user_obj.username
    else:
        guest_id = request.session.get('guest_id', 'guest_user_session')
        profile, _ = UserProfile.objects.get_or_create(guest_identifier=guest_id, defaults={'display_name': 'Guest'})
        display_name = "Guest"
        header_userid = "Guest"

    request.session['display_name'] = display_name

    show_welcome_modal = request.session.pop('trigger_welcome_modal', False)
    is_new_user_login = request.session.pop('is_new_user_login', False)

    group_form = GroupForm(initial={'members_list': display_name})
    budget_form = BudgetForm()

    current_real_month = datetime.now().strftime('%Y-%m')
    selected_month = request.GET.get('month', current_real_month)
    if len(selected_month) != 7:
        selected_month = current_real_month

    if user_obj:
        curr_month_budget = Budget.objects.filter(user=user_obj, month_year=current_real_month).first()
    else:
        g_id = request.session.get('guest_id', 'guest_user_session')
        curr_month_budget = Budget.objects.filter(guest_name='Guest', month_year=current_real_month, user=None).first()

    show_month_end_prompt = False
    if not curr_month_budget or curr_month_budget.monthly_limit <= 0:
        if not request.session.get(f'prompted_month_{current_real_month}', False):
            show_month_end_prompt = True
            request.session[f'prompted_month_{current_real_month}'] = True

    if request.method == 'POST':
        if 'create_group' in request.POST:
            group_form = GroupForm(request.POST)
            if group_form.is_valid():
                group = group_form.save(commit=False)
                if user_obj:
                    group.created_by = user_obj
                else:
                    group.created_by = None
                    group.guest_identifier = request.session.get('guest_id', '')
                group.save()
                messages.success(request, "Group / Trip created successfully with independent ledger!")
                return redirect('dashboard')
            else:
                messages.error(request, "Validation Error: Please check group details and member names.")
                
        elif 'set_budget' in request.POST:
            budget_form = BudgetForm(request.POST)
            if budget_form.is_valid():
                limit = budget_form.cleaned_data['monthly_limit']
                m_year = budget_form.cleaned_data['month_year']
                
                if limit < 0:
                    messages.error(request, "Validation Error: Budget limit cannot be negative!")
                    return redirect('dashboard')

                if user_obj:
                    b_obj, created = Budget.objects.get_or_create(user=user_obj, month_year=m_year)
                else:
                    b_obj, created = Budget.objects.get_or_create(guest_name='Guest', month_year=m_year, user=None)
                
                b_obj.monthly_limit = limit
                b_obj.dismiss_warning = False
                b_obj.save()
                messages.success(request, f"Monthly budget successfully saved/updated for {m_year}!")
                return redirect(f'/dashboard/?month={m_year}')

    # STRICT FILTERING: Guest sees ONLY groups created by their specific guest_identifier
    if user_obj:
        groups = Group.objects.filter(created_by=user_obj).order_by('-id')
        personal_expenses_db = PersonalExpense.objects.filter(user=user_obj).order_by('-date')
    else:
        g_id = request.session.get('guest_id', 'guest_user_session')
        groups = Group.objects.filter(created_by=None, guest_identifier=g_id).order_by('-id')
        personal_expenses_db = PersonalExpense.objects.filter(guest_identifier=g_id).order_by('-date')

    filtered_personal_expenses = [
        pe for pe in personal_expenses_db 
        if pe.date and pe.date.strftime('%Y-%m') == selected_month
    ]

    total_month_spent = sum(float(pe.amount) for pe in filtered_personal_expenses)

    if user_obj:
        selected_budget_obj = Budget.objects.filter(user=user_obj, month_year=selected_month).first()
    else:
        selected_budget_obj = Budget.objects.filter(guest_name='Guest', month_year=selected_month, user=None).first()

    budget_limit = float(selected_budget_obj.monthly_limit) if selected_budget_obj else 0.0
    remaining_budget = budget_limit - total_month_spent if budget_limit > 0 else 0.0
    
    show_warning = False
    if budget_limit > 0 and total_month_spent > budget_limit and selected_budget_obj and not selected_budget_obj.dismiss_warning:
        show_warning = True

    past_six_months_summary = []
    for i in range(5, -1, -1):
        target_date = datetime.now() - relativedelta(months=i)
        m_str = target_date.strftime('%Y-%m')
        m_label = target_date.strftime('%B %Y')
        
        m_spent = sum(float(pe.amount) for pe in personal_expenses_db if pe.date and pe.date.strftime('%Y-%m') == m_str)
        if user_obj:
            b_obj = Budget.objects.filter(user=user_obj, month_year=m_str).first()
        else:
            b_obj = Budget.objects.filter(guest_name='Guest', month_year=m_str, user=None).first()
        
        b_lim = float(b_obj.monthly_limit) if b_obj else 0.0
        past_six_months_summary.append({
            'month_str': m_str,
            'month_label': m_label,
            'spent': m_spent,
            'limit': b_lim,
            'breached': b_lim > 0 and m_spent > b_lim
        })

    balance_summary = []
    for g in groups:
        if g.is_settled:
            continue
        g_expenses = g.expenses.all()
        members = [m.strip() for m in g.members_list.split(',') if m.strip()]
        num_members = len(members) if len(members) > 0 else g.num_members
        if num_members <= 0:
            num_members = 1
        
        total_spent_g = sum(float(e.amount) for e in g_expenses)
        share_per_person = total_spent_g / num_members
        
        paid_summary = {m: 0 for m in members}
        for e in g_expenses:
            payer = e.paid_by.strip()
            matched = next((m for m in members if m.lower() == payer.lower()), payer)
            if matched not in paid_summary:
                paid_summary[matched] = 0
            paid_summary[matched] += float(e.amount)

        user_paid_amt = paid_summary.get(display_name, 0)
        user_balance = user_paid_amt - share_per_person
        if user_balance != 0:
            balance_summary.append({
                'group_name': g.name,
                'amount': abs(user_balance),
                'type': 'gets_back' if user_balance > 0 else 'needs_pay'
            })

    has_budget_set = True if selected_budget_obj and selected_budget_obj.monthly_limit > 0 else False

    context = {
        'username': display_name,
        'header_userid': header_userid,
        'is_guest': is_guest,
        'show_welcome_modal': show_welcome_modal,
        'is_new_user_login': is_new_user_login,
        'show_month_end_prompt': show_month_end_prompt,
        'current_real_month': current_real_month,
        'group_form': group_form,
        'budget_form': budget_form,
        'groups': groups,
        'personal_expenses': filtered_personal_expenses,
        'selected_month': selected_month,
        'current_month_spent': total_month_spent,
        'budget_limit': budget_limit,
        'remaining_budget': remaining_budget,
        'has_budget_set': has_budget_set,
        'past_six_months_summary': past_six_months_summary,
        'balance_summary': balance_summary,
        'show_warning': show_warning,
    }
    return render(request, 'core/dashboard.html', context)

def dismiss_budget_warning_view(request):
    current_month_str = datetime.now().strftime('%Y-%m')
    if request.user.is_authenticated:
        b_obj = Budget.objects.filter(user=request.user, month_year=current_month_str).first()
        if b_obj:
            b_obj.dismiss_warning = True
            b_obj.save()
    return redirect('dashboard')

def delete_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    user_obj = request.user if request.user.is_authenticated else None
    display_name = request.session.get('display_name', 'User')
    
    expenses = group.expenses.all()
    total_spent_g = sum(float(e.amount) for e in expenses)
    members = [m.strip() for m in group.members_list.split(',') if m.strip()]
    num_members = len(members) if len(members) > 0 else group.num_members
    if num_members <= 0:
        num_members = 1
    share_per_person = total_spent_g / num_members
    
    paid_summary = {m: 0 for m in members}
    for e in expenses:
        payer = e.paid_by.strip()
        matched = next((m for m in members if m.lower() == payer.lower()), payer)
        if matched not in paid_summary:
            paid_summary[matched] = 0
        paid_summary[matched] += float(e.amount)

    user_paid_amt = paid_summary.get(display_name, 0)
    user_balance = user_paid_amt - share_per_person
    breached = group.group_budget > 0 and total_spent_g > float(group.group_budget)

    ArchivedGroupHistory.objects.create(
        user=user_obj if user_obj else None,
        guest_identifier=request.session.get('guest_id', '') if not user_obj else '',
        group_name=group.name,
        description=group.description,
        total_spent=total_spent_g,
        group_budget=group.group_budget,
        user_paid=user_paid_amt,
        user_share=share_per_person,
        user_balance=user_balance,
        budget_breached=breached,
        members_summary=group.members_list
    )

    group.delete()
    messages.success(request, "Group deleted, but basic trip record has been safely preserved in All Groups History archive!")
    return redirect('dashboard')

def delete_expense_view(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    group_id = expense.group.id
    expense.delete()
    messages.success(request, "Expense deleted successfully!")
    return redirect('group_detail', group_id=group_id)

def delete_member_view(request, group_id, member_name):
    group = get_object_or_404(Group, id=group_id)
    members = [m.strip() for m in group.members_list.split(',') if m.strip()]
    updated_members = [m for m in members if m.lower() != member_name.lower()]
    group.members_list = ", ".join(updated_members)
    group.num_members = len(updated_members) if len(updated_members) > 0 else 1
    group.save()
    
    group.expenses.filter(paid_by__iexact=member_name).delete()
    messages.success(request, f"Member '{member_name}' and their expenses deleted successfully.")
    return redirect('group_detail', group_id=group.id)

def settle_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    group.is_settled = True
    group.save()
    messages.success(request, f"Group '{group.name}' has been successfully settled & cleared!")
    return redirect('group_detail', group_id=group.id)

def group_detail_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    expenses = group.expenses.all().order_by('-date')
    
    display_name = request.session.get('display_name', 'User')
    expense_form = ExpenseForm(initial={'paid_by': display_name})
    
    settlement_calculated = request.session.get(f'settlement_calc_{group_id}', False)
    settlement_results = None
    members = [m.strip() for m in group.members_list.split(',') if m.strip()]

    if request.method == 'POST':
        if 'add_expense' in request.POST:
            expense_form = ExpenseForm(request.POST)
            if expense_form.is_valid():
                payer = expense_form.cleaned_data.get('paid_by').strip()
                members_lower = [m.lower() for m in members]
                
                if payer.lower() not in members_lower:
                    messages.error(request, f"Validation Error: '{payer}' is not a registered member of this group!")
                else:
                    expense = expense_form.save(commit=False)
                    expense.group = group
                    expense.save()
                    request.session[f'settlement_calc_{group_id}'] = False
                    messages.success(request, "Group expense added successfully!")
                
                return redirect('group_detail', group_id=group.id)
            else:
                messages.error(request, "Validation Error: Please check expense details.")
                
        elif 'calculate_expenses' in request.POST:
            request.session[f'settlement_calc_{group_id}'] = True
            settlement_calculated = True
            messages.success(request, "Settlement calculated successfully! PDF download is now unlocked.")

    total_spent = sum(float(exp.amount) for exp in expenses)
    group_budget_breached = group.group_budget > 0 and total_spent > float(group.group_budget)

    num_members = len(members) if len(members) > 0 else group.num_members
    if num_members <= 0:
        num_members = 1
    share_per_person = total_spent / num_members
    
    paid_summary = {m: 0 for m in members}
    for exp in expenses:
        payer = exp.paid_by.strip()
        matched_member = next((m for m in members if m.lower() == payer.lower()), payer)
        if matched_member not in paid_summary:
            paid_summary[matched_member] = 0
        paid_summary[matched_member] += float(exp.amount)

    settlement_results = []
    all_involved = set(members) | set(paid_summary.keys())
    for member in all_involved:
        paid = paid_summary.get(member, 0)
        balance = paid - share_per_person
        settlement_results.append({
            'member': member,
            'paid': paid,
            'share': share_per_person,
            'balance': balance,
        })

    context = {
        'group': group,
        'expenses': expenses,
        'expense_form': expense_form,
        'total_spent': total_spent,
        'group_budget_breached': group_budget_breached,
        'settlement_calculated': settlement_calculated,
        'settlement_results': settlement_results,
        'members_list': members,
    }
    return render(request, 'core/group_detail.html', context)

def export_group_pdf_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not request.session.get(f'settlement_calc_{group_id}', False):
        messages.error(request, "Access Denied: Please click 'Calculate Settlements' before downloading the settlement PDF report!")
        return redirect('group_detail', group_id=group.id)

    expenses = group.expenses.all().order_by('-date')
    members = [m.strip() for m in group.members_list.split(',') if m.strip()]
    num_members = len(members) if len(members) > 0 else group.num_members
    if num_members <= 0:
        num_members = 1
    
    total_spent = sum(float(e.amount) for e in expenses)
    share_per_person = total_spent / num_members

    paid_summary = {m: 0 for m in members}
    for exp in expenses:
        payer = exp.paid_by.strip()
        matched = next((m for m in members if m.lower() == payer.lower()), payer)
        if matched not in paid_summary:
            paid_summary[matched] = 0
        paid_summary[matched] += float(exp.amount)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{group.name}_Settlement_Report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1e3a8a'), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#4b5563'), spaceAfter=12)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#1f2937'), spaceBefore=12, spaceAfter=6)

    elements.append(Paragraph("KAPTAN-HETM - Group Settlement Report", title_style))
    elements.append(Paragraph(f"<b>Group:</b> {group.name} | <b>Total Spend:</b> ₹{total_spent} | <b>Budget:</b> ₹{group.group_budget}", subtitle_style))
    elements.append(Paragraph(f"<b>Members:</b> {group.members_list}", subtitle_style))
    elements.append(Paragraph("Final Settlement & Dues Breakdown", heading_style))

    table_data = [['Member Name', 'Total Paid (INR)', 'Equal Share (INR)', 'Net Dues / Status']]
    for member in members:
        paid = paid_summary.get(member, 0)
        balance = paid - share_per_person
        if balance > 0:
            status = f"Gets back ₹{abs(balance):.2f}"
        elif balance < 0:
            status = f"Needs to pay ₹{abs(balance):.2f}"
        else:
            status = "Fully Settled"
        table_data.append([member, f"₹{paid:.2f}", f"₹{share_per_person:.2f}", status])

    settle_table = Table(table_data, colWidths=[130, 110, 110, 190])
    settle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f3f4f6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))

    elements.append(settle_table)
    doc.build(elements)
    return response

def global_group_expenses_view(request):
    is_guest = request.session.get('is_guest_session', False)
    if not request.user.is_authenticated and not request.session.get('guest_id'):
        return redirect('login')

    user_obj = request.user if request.user.is_authenticated else None
    display_name = request.session.get('display_name', 'User')

    if user_obj:
        groups = Group.objects.filter(created_by=user_obj).order_by('-id')
        archives = ArchivedGroupHistory.objects.filter(user=user_obj).order_by('-deleted_at')
    else:
        g_id = request.session.get('guest_id', 'guest_user_session')
        groups = Group.objects.filter(created_by=None, guest_identifier=g_id).order_by('-id')
        archives = ArchivedGroupHistory.objects.filter(guest_identifier=g_id).order_by('-deleted_at')

    all_group_records = []
    for g in groups:
        g_expenses = g.expenses.all().order_by('-date')
        members = [m.strip() for m in g.members_list.split(',') if m.strip()]
        num_members = len(members) if len(members) > 0 else g.num_members
        if num_members <= 0:
            num_members = 1
            
        total_spent_g = sum(float(item.amount) for item in g_expenses)
        share_per_person = total_spent_g / num_members
        
        paid_summary = {m: 0 for m in members}
        for item in g_expenses:
            payer = item.paid_by.strip()
            matched = next((m for m in members if m.lower() == payer.lower()), payer)
            if matched not in paid_summary:
                paid_summary[matched] = 0
            paid_summary[matched] += float(item.amount)

        user_paid_amt = paid_summary.get(display_name, 0)
        user_balance = user_paid_amt - share_per_person

        all_group_records.append({
            'is_archived': False,
            'group': g,
            'expenses': g_expenses,
            'total_spent': total_spent_g,
            'user_paid': user_paid_amt,
            'user_balance': user_balance,
            'budget_breached': g.group_budget > 0 and total_spent_g > float(g.group_budget)
        })

    context = {
        'username': display_name,
        'header_userid': user_obj.email if (user_obj and user_obj.email) else (user_obj.username if user_obj else "Guest"),
        'is_guest': is_guest,
        'all_group_records': all_group_records,
        'archives': archives,
    }
    return render(request, 'core/global_group_expenses.html', context)

def info_view(request):
    return render(request, 'core/info.html')