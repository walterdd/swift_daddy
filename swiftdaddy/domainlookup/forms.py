from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30, default='dwalter', widget = forms.TextInput(attrs = {'class': 'form-control'}))
    password = forms.CharField(max_length=30, default='swiftdaddy', widget = forms.PasswordInput(attrs = {'class': 'form-control'}))
