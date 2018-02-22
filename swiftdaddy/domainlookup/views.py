from django.shortcuts import render
from .domain_lookup import *
from .preprocess import *
from tqdm import tqdm
from django.core.mail import EmailMessage, send_mail
from background_task import background
from django.template.loader import get_template

from .models import Domain

@background(schedule=0)
def generate_result(queries):
    def generator(choices):
        for choice in choices:
            yield choice.name
    queries = [query.strip() for query in queries]
    result = dict()
    for query in tqdm(queries):
        domain, length, zone = preprocess_domain(query)
        choices = Domain.objects.filter(length__gte=length-2).filter(length__lte=length*2)
        res = findMatches(generator(choices), domain)
        res = [r[0] for r in res]
        result[query] = res
    result = pd.DataFrame(result)

    preview = ', '.join(queries[:3])
    preview += ' и др.' if len(queries) > 3 else ''
    email = EmailMessage(
        'SwiftDaddy результаты для запросов: {}'.format(preview),
        'Привет, Митя! \nЛови похожие домены по твоим запросам: {} в приложенном к письму файле.'.format(preview),
        'myswiftdaddy@gmail.com',
        ['dasha-walter@yandex.ru']
    )
    file = result.to_csv(sep=';')
    email.attach('{}.csv'.format(preview), file, 'text/csv')
    email.send()

@background(schedule=0)
def read_database(file):
    filelines = file.split('\n')
    for line in tqdm(filelines):
        line = line.strip()
        data = line.split(';')
        if len(data) != 5:
            continue
        name, registrar, start_date, end_date, delegated = data
        name, length, zone = preprocess_domain(name)
        if zone is None:
            continue
        domain = Domain()
        domain.name = name
        domain.length = length
        domain.zone = zone
        domain.registrar = registrar
        domain.start_date = start_date
        domain.end_date = end_date
        domain.save()

# @background(schedule=0)
def send_greetings():
    template = get_template('cake.html')
    content = template.render()
    send_mail(subject='Happy Birthday, SwiftDaddy!',
              message='',
              html_message=content,
              from_email='myswiftdaddy@gmail.com',
              recipient_list=['dasha-walter@yandex.ru'])
    print('greetings sent')

def greetings(request):
    print('sending greetings')
    send_greetings()
    return render(request, 'cake.html', {})

def desktop(request):
    return render(request, 'search.html', {})

def card(request):
    return render(request, 'card.html', {})

def database(request):
    return render(request, 'database.html', {})

def upload_domains(request):
    if request.method == "POST":
        Domain.objects.all().delete()
        domains_file = request.FILES['domains_file']
        read_database(domains_file.read().decode('UTF-8'), schedule=0)
    else:
        return render(request, 'search.html', {})

    return render(request, 'search.html', {})

def text_query(request):
    if request.method == "GET":
        search_text = request.GET['text_query']
    else:
        return render(request, 'search.html', {})

    queries = search_text.split(',')
    generate_result(queries)

    return render(request, 'search.html', {'email' : 'dwalter@yandex.ru'})

def file_query(request):
    if request.method == "POST":
        file = request.FILES['file_query']
    else:
        return render(request, 'search.html', {})
    queries = file.read().decode('UTF-8').split('\n')
    generate_result(queries)

    return render(request, 'search.html', {'email' : 'dwalter@yandex.ru'})
