import sys

from django.shortcuts import render
from tqdm import tqdm
from django.core.mail import EmailMessage, send_mail
from background_task import background
from django.template.loader import get_template
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.db import OperationalError

from .models import Domain, Meta
from .domain_lookup import *
from .preprocess import *
from .forms import LoginForm
from .utils import *
from time import time

from multiprocessing import Pool
from contextlib import contextmanager


@contextmanager
def poolcontext(*args, **kwargs):
    pool = Pool(*args, **kwargs)
    yield pool
    pool.terminate()


@background(schedule=0)
def generate_result(queries, email_address, username):
    N_RESULTS = 30
    queries = [query.strip() for query in queries]
    start_with = dict()
    end_with = dict()
    result = dict()
    for query in tqdm(queries):
        domain, length, zone = preprocess_domain(query)
        print('query: {}'.format(query))

        N = Domain.objects.all().count()
        print('Domain database size: %d' % N)
        print('Number of candidate domains: %d' %
              Domain.objects.filter(length__gte=length-2).filter(length__lte=length+5).count())

        all_domains = set()

        start_time = time()
        start_with_choices = Domain.objects.filter(name__startswith=domain)
        start_with[query] = [choice.name for choice in start_with_choices if choice.name not in all_domains]
        domain_wo_hy = removeNonAlphanum(domain)
        if domain_wo_hy != domain:
            for d in Domain.objects.filter(name__startswith=domain_wo_hy):
                start_with[query].append(d.name)
        print('Start with selection: {}'.format(time() - start_time))
        start_with[query] = sorted(start_with[query])
        all_domains.update(start_with[query])

        start_time = time()
        end_with_choices = Domain.objects.filter(name__endswith=domain)
        end_with[query] = [choice.name for choice in end_with_choices if choice.name not in all_domains]
        if domain_wo_hy != domain:
            for d in Domain.objects.filter(name__endswith=domain_wo_hy):
                end_with[query].append(d.name)
        print('End with selection: {}'.format(time() - start_time))
        end_with[query] = sorted(end_with[query])
        all_domains.update(end_with[query])

        n_workers = 4
        chunk = N // n_workers
        args = zip([N_RESULTS for i in range(n_workers)],
                   [i for i in range(n_workers)],
                   [chunk for _ in range(n_workers)],
                   repeat(domain, n_workers))
        print('Start map')
        with poolcontext(processes=n_workers) as pool:
            res = pool.starmap(findMatches, args)

        final_res = []
        for r in res:
            final_res += r
        final_res = sorted(final_res, key=lambda x: x[1])
        final_res = final_res[:N_RESULTS]

        final_res = [r for r in final_res if r[0] not in all_domains]
        all_domains.update([r[0] for r in final_res])

        for i in range(len(final_res)):
            final_res[i] = [str(r) for r in final_res[i]]
        final_res = [' '.join(res) for res in final_res]
        result[query] = final_res

    def pad_dict(d):
        values = d.values()
        length = max([len(val) for val in values])
        for key in d.keys():
            cur_len = len(d[key])
            if cur_len < length:
                for _ in range(length-cur_len):
                    d[key].append(None)
        return d

    pad_dict(start_with)
    pad_dict(end_with)
    pad_dict(result)

    result = pd.DataFrame(result)
    start_with = pd.DataFrame(start_with)
    end_with = pd.DataFrame(end_with)

    preview = ', '.join(queries[:3])
    preview += ' и др.' if len(queries) > 3 else ''
    print('email_address', email_address)
    file = (result.to_csv(sep='\t') +
            '\n\nStart matches:\n' + start_with.to_csv(sep='\t', header=None) +
            '\n\nEnd matches:\n' + end_with.to_csv(sep='\t', header=None))

    email = EmailMessage(
        'SwiftDaddy результаты для запросов: {}'.format(preview),
        'Привет, {0}! \nЛови похожие домены по твоим запросам: {1} в приложенном к письму файле.'.format(username,
                                                                                                         preview),
        'myswiftdaddy@gmail.com',
        [email_address]
    )
    email.attach('{}.xls'.format(preview), file, 'text/xls')
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

        if length >= 15:
            continue

        def count_alphas(name):
            alphas = 0
            for c in name:
                if c.isalpha():
                    alphas += 1
            return float(alphas) / len(name)

        alphas = count_alphas(name)
        if alphas < 0.7:
            continue

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

    meta = Meta.objects.all()
    if len(meta) == 0:
        meta = Meta()
        meta.n_domains = domain_id
    else:
        meta = meta[0]
        meta.n_domains = domain_id
    meta.save()

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
    # send_greetings()
    return render(request, 'cake.html', {})

def desktop(request):
    if request.user.is_authenticated():
        return render(request, 'search.html', {})
    form = LoginForm()
    return render(request, 'welcome.html', {'form' : form})

def confetti(request):
    if request.user.is_authenticated():
        return render(request, 'search-confetti.html', {})
    form = LoginForm()
    return render(request, 'welcome.html', {'form' : form})

def database(request):
    if request.user.is_authenticated():
        return render(request, 'database.html', {})
    form = LoginForm()
    return render(request, 'welcome.html', {'form' : form})

def upload_domains(request):
    if request.method == "POST":
        Domain.objects.all().delete()
        domains_file = request.FILES['domains_file']
        try:
            read_database(domains_file.read().decode('UTF-8'), schedule=0)
        except OperationalError:
            return render(request, 'oops.html', {})
    else:
        return render(request, 'search.html', {})

    return render(request, 'search.html', {})

def text_query(request):
    if request.method == "GET":
        search_text = request.GET['text_query']
    else:
        return render(request, 'search.html', {})
    if request.user.is_authenticated():
        email_address = request.user.email
    else:
        form = LoginForm()
        return render(request, 'welcome.html', {'form' : form})
    username = request.user.first_name
    queries = search_text.split()
    try:
        generate_result(queries, email_address, username)
    except OperationalError:
        return render(request, 'oops.html', {})

    return render(request, 'search.html', {'email' : email_address})


def file_query(request):
    if request.method == "POST":
        file = request.FILES['file_query']
    else:
        return render(request, 'search.html', {})
    queries = file.read().decode('UTF-8').split('\n')
    try:
        generate_result(queries)
    except OperationalError:
        return render(request, 'oops.html', {})

    return render(request, 'search.html', {'email' : 'dwalter@yandex.ru'})


def welcome(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data.get('username'), password=form.cleaned_data.get('password'))
            if user is not None:
                print('user found!')
                login(request, user)
                return HttpResponseRedirect('/confetti')
    form = LoginForm()
    return render(request, 'welcome.html', {'form' : form})

def csrf_failure(request, reason):
    return welcome(request)