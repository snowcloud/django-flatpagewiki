""" views for flatpagewiki app

"""
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import redirect_to_login
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.xheaders import populate_xheaders
from django.http import Http404
from django.http import HttpResponseRedirect
from django import forms
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.html import escape


DEFAULT_TEMPLATE = 'wiki/default.html'
DEFAULT_TEMPLATE_NEW = 'wiki/default_new_page.html'

class WikiPageForm(forms.Form):
    url = forms.CharField(max_length=100)
    title = forms.CharField(max_length=100)
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 20, 'cols': 80, 'class': 't_area'}))

@permission_required('flatpages.new_flatpage')
def newpage(request, url):
    """
    New Flat page wiki view.

    template hardcoded for now
    """

    if not request.user.is_authenticated():
        raise Http404
    
    from urlparse import urlparse
    # if referer then use it or default '/'
    ref = urlparse(request.META.get('HTTP_REFERER', ''))[2]
    # use hidden field if it's there
    ref = request.REQUEST.get('ref', ref)
    if ref == '':
        ref = '/'

    #return render_to_response(DEFAULT_TEMPLATE_NEW,  
    #    RequestContext( request, { 'url': url, 'ref': ref } ))
    
    if request.method == 'POST':
        if request.POST['result'] == 'Cancel':
            return HttpResponseRedirect(ref)
        else:
            form = WikiPageForm(request.POST)
            if form.is_valid():
                try:
                    f = get_object_or_404(FlatPage, url__exact=url, sites__id__exact=settings.SITE_ID)
                except Http404:
                    f = FlatPage()
                    f.url = str(form.clean()['url'])
                    f.title = form.clean()['title']
                    f.content = str(form.clean()['content'])
                    f.enable_comments = False
                    f.registration_required = False
                    f.save()
                    # need to save get a pk before adding a M2M
                    s = Site.objects.get_current()
                    f.sites.add(s)
                    f.save()
                    return HttpResponseRedirect(f.url)

    else:
        form = WikiPageForm({'url': url, })
        form.ignore_errors = True
        #form.errors().clear()

    response = render_to_response(DEFAULT_TEMPLATE_NEW,  
        RequestContext( request, { 'form': form, 'ref': ref }) )
    #populate_xheaders(request, response, FlatPage, f.id)
    return response
    

def showpage(request, url):
    """
    Flat page wiki view.
    
    template hardcoded for now
    """

    if not url.startswith('/'):
        url = "/" + url
    if not url.endswith('/'):
        url = url + "/"
    wikipath = url.split('/')[1]
    if not wikipath in settings.FLATPAGEWIKI_PATHS:
        raise Http404
    try:
        f = get_object_or_404(FlatPage, url__exact=url, sites__id__exact=settings.SITE_ID)
    except Http404:
        return newpage(request, url)

    # If registration is required for accessing this page, and the user isn't
    # logged in, redirect to the login page.
    if f.registration_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)
    if f.template_name:
        t = 'wiki/%s' % f.template_name
    else:
        t = DEFAULT_TEMPLATE

    edit = '0'
    if request.method == 'POST':
        if not request.user.has_perm('flatpages.change_flatpage'):
            raise Http404
        if request.POST['result'] == 'Cancel':
            return HttpResponseRedirect(f.url)
        else:
            if not request.user.is_authenticated():
                return redirect_to_login(request.path)
            form = WikiPageForm(request.POST)
            if form.is_valid():
                f.title = form.cleaned_data['title']
                f.content = (form.cleaned_data['content'])
                if settings.EMAIL_FLATPAGE_SAVES:
                    fp_change(request, f)
                f.save()
                return HttpResponseRedirect(f.url)
    else:
        if request.user.has_perm('flatpages.change_flatpage'):
            edit = request.GET.get('edit', '0') 
        form = WikiPageForm({'url': f.url, 'title': f.title, 'content': f.content })

    response = render_to_response(t,  
        RequestContext( request, { 'form': form, 'object': f, 'edit': edit  }) )
    populate_xheaders(request, response, FlatPage, f.id)
    return response
        
def fp_change(req, instance):
    """temp check for unknown access to flatpage edits"""
    if req.user.id:
        uname = req.user.username
    else:
        uname = 'anonymoususer'
    txt = '\n'.join((uname, req.META['REMOTE_ADDR'], instance.content))
    # txt = (request.REQUEST['REMOTE_ADDR']) 
    send_mail('[SMG web] FlatPage changed',
        'on page: %s%s\n-------\n%s\n%s' % 
        (settings.APP_BASE[:-1], instance.get_absolute_url(), escape(instance.title), escape(txt)), 
        'derek.hoy@gmail.com',
        ['derek.hoy@gmail.com'], fail_silently=False)    


