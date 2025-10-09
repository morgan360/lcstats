from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

# Signup view — handles registration
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # after signup, go to login page
    else:
        form = UserCreationForm()
    return render(request, 'students/signup.html', {'form': form})


# Dashboard view — shows student profile info (requires login)
@login_required
def dashboard_view(request):
    profile, created = request.user.studentprofile, False
    try:
        profile = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)
    return render(request, 'students/dashboard.html', {'profile': profile})
