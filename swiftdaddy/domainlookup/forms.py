from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30, initial='dwalter', widget = forms.TextInput(attrs = {'class': 'form-control'}))
    password = forms.CharField(max_length=30, initial='swiftdaddy', widget = forms.PasswordInput(attrs = {'class': 'form-control'}))
