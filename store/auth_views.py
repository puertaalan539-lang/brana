# store/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm


def user_register(request):
    if request.user.is_authenticated:
        return redirect('store:catalog')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'¡Bienvenida, {user.email}! 🌸')
        return redirect('store:catalog')

    return render(request, 'auth/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('store:catalog')

    form  = LoginForm(request.POST or None)
    error = ''

    if request.method == 'POST' and form.is_valid():
        email    = form.cleaned_data['email'].lower()
        password = form.cleaned_data['password']
        user     = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'store:catalog')
            return redirect(next_url)
        error = 'Correo o contraseña incorrectos.'

    return render(request, 'auth/login.html', {'form': form, 'error': error})


def user_logout(request):
    logout(request)
    return redirect('store:catalog')


@login_required(login_url='/cuenta/login/')
def user_profile(request):
    return render(request, 'auth/profile.html')