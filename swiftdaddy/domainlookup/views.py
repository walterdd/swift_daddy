from django.shortcuts import render
from tqdm import tqdm
from django.core.mail import EmailMessage, send_mail
from background_task import background
from django.template.loader import get_template
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect

from .models import Domain
from .domain_lookup import *
from .preprocess import *
from .forms import LoginForm
from time import time

from multiprocessing import Pool
from contextlib import contextmanager

@contextmanager
def poolcontext(*args, **kwargs):
    pool = Pool(*args, **kwargs)
    yield pool
    pool.terminate()


@background(schedule=0)
def generate_result(queries):
    N = 20
    queries = [query.strip() for query in queries]
    result = dict()
    for query in tqdm(queries):
        domain, length, zone = preprocess_domain(query)
        print('query: {}'.format(query))
        start_time = time()
        choices = Domain.objects.filter(length__gte=length-2).filter(length__lte=length*2)
        print('Filter domains: {}'.format(time() - start_time))

        N = len(choices)
        n_workers = 4
        chunk = N // n_workers
        args = zip([Domain.objects.filter(id__gte=i*chunk).filter(id__lte=i * chunk + chunk)
                   for i in range(n_workers)], repeat(domain, n_workers))
        with poolcontext(processes=n_workers) as pool:
            res = pool.starmap(findMatches, args)

        final_res = []
        for r in res:
            final_res += r
        final_res = sorted(final_res, key=lambda x: x[1])
        final_res = final_res[:N]
        final_res = [r[0] for r in final_res]
        result[query] = final_res
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
    domain_id = 0
    for line in tqdm(filelines):
        line = line.strip()
        data = line.split(';')
        if len(data) != 5:
            continue
        name, registrar, start_date, end_date, delegated = data
        name, length, zone = preprocess_domain(name)
        if zone is None:
            continue

        # if length >= 15:
        #     continue
        #
        # def count_alphas(name):
        #     alphas = 0
        #     for c in name:
        #         if c.isalpha():
        #             alphas += 1
        #     return float(alphas) / len(name)
        #
        # alphas = count_alphas(name)
        # if alphas < 0.7:
        #     continue
        #
        domain = Domain()
        domain.id = domain_id
        domain.name = name
        domain.length = length
        domain.zone = zone
        domain.registrar = registrar
        domain.start_date = start_date
        domain.end_date = end_date
        domain.save()

        domain_id += 1

@background(schedule=0)
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
    if request.user.is_authenticated():
        return render(request, 'search.html', {})
    form = LoginForm()
    return render(request, 'balloons2.html', {'form' : form})

def card(request):
    return render(request, 'card.html', {})

def database(request):
    if request.user.is_authenticated():
        return render(request, 'database.html', {})
    form = LoginForm()
    return render(request, 'balloons2.html', {'form' : form})

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


def welcome(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data.get('username'), password=form.cleaned_data.get('password'))
            if user is not None:
                print('user found!')
                login(request, user)
                return HttpResponseRedirect('/')
    form = LoginForm()
    return render(request, 'balloons2.html', {'form' : form})

def csrf_failure(request, reason):
    return welcome(request)