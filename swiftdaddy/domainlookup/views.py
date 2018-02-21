from django.shortcuts import render
from .process import *
from tqdm import tqdm
from django.core.mail import EmailMessage

from .models import Domain

def read_input(file):
    for line in tqdm(file.readlines()):
        line = line.decode('UTF-8').strip()
        data = line.split(';')
        if len(data) != 5:
            continue
        name, registrar, start_date, end_date, delegated = data
        domain = Domain()
        domain.name = name
        domain.registrar = registrar
        domain.start_date = start_date
        domain.end_date = end_date
        domain.save()

def send_email():
    email = EmailMessage(
        'Hello',
        'Body goes here',
        'myswiftdaddy@gmail.com',
        ['dasha-walter@yandex.ru']
    )
    email.send()



def desktop(request):
    return render(request, 'search.html', {})

def database(request):
    return render(request, 'database.html', {})

def upload_domains(request):
    print('upload_domains')
    if request.method == "POST":
        Domain.objects.all().delete()
        domains_file = request.FILES['domains_file']
        print('domains_file', domains_file)
        read_input(domains_file)
    else:
        return render(request, 'search.html', {})

    return render(request, 'search.html', {})

def text_query(request):
    print('text_query')
    if request.method == "GET":
        search_text = request.GET['text_query']
        print('search_text', search_text)
    else:
        return render(request, 'search.html', {})

    send_email()
    return render(request, 'search.html', {'email' : 'dwalter@yandex.ru'})

def file_query(request):
    print('file_query')
    if request.method == "POST":
        search_text = request.FILES['file_query']
        print('search_text', search_text)
    else:
        search_text = ''
        return render(request, 'search.html', {})

    return render(request, 'search.html', {'email' : 'dwalter@yandex.ru'})
