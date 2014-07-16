# Copyright Evan Hazlett and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms
from hosts.models import Host
from images.models import Image
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Button
from crispy_forms.bootstrap import FieldWithButtons, StrictButton, FormActions
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

def get_available_hosts():
    return Host.objects.filter(enabled=True)

def get_image_choices():
    hosts = get_available_hosts()
    choices = []
    images = Image.objects.filter(host__in=hosts).order_by('repository').values_list(
            'repository', flat=True).order_by('repository').distinct()
    for i in images:
        repo = i
        if repo.find('<none>') == -1:
            d = (repo, repo)
            choices.append(d)
    return choices

class CreateContainerForm(forms.Form):
    image = forms.ChoiceField(required=True)
    name = forms.CharField(required=False, help_text=_('container name (used in links)'))
    hostname = forms.CharField(required=False)
    description = forms.CharField(required=False)
    command = forms.CharField(required=False)
    cpu_shares = forms.ChoiceField(required=True)
    memory = forms.CharField(required=False, initial='4096', max_length=8,
        help_text='Memory in MB')
    ip_range = forms.CharField(required=True, help_text=_('range used to define IPs (i.e. 10-20 --> 192.168.88.10 ... 192.168.88.19)'))
    environment = forms.CharField(required=False,
        help_text='key=value space separated pairs')
    ports = forms.CharField(required=False, help_text=_('space separated (i.e. 8000 8001:8001 127.0.0.1:80:80 )'))
    links = forms.CharField(required=False, help_text=_('space separated (i.e. redis:db)'))
    volume = forms.CharField(required=False, help_text='container volume (i.e. /mnt/volume)')
    volumes_from = forms.CharField(required=False,
        help_text='mount volumes from specified container')
    hosts = forms.MultipleChoiceField(required=True)
    network_disabled = forms.BooleanField(required=False, initial=True)
    private = forms.BooleanField(required=False)
    privileged = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(CreateContainerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                None,
                'image',
                'name',
                'hostname',
                'command',
                'description',
                'cpu_shares',
                'memory',
                'ip_range',
                'environment',
                'ports',
                'links',
                'volume',
                'volumes_from',
                'hosts',
                'network_disabled',
                'private',
                'privileged'
            ),
            FormActions(
                Submit('save', _('Create'), css_class="btn btn-lg btn-success"),
            )
        )
        self.helper.form_id = 'form-create-container'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.create_container')
        self.helper.help_text_inline = True
        self.fields['image'].choices = [('', '----------')] + \
            [x for x in get_image_choices()]
        self.fields['hosts'].choices = \
            [(x.id, x.name) for x in get_available_hosts()]
        self.fields['cpu_shares'].choices = [(4 , 4)] + [(2, 2), (8, 8)]

class ImportRepositoryForm(forms.Form):
    repository = forms.CharField(help_text='i.e. ehazlett/logstash')
    hosts = forms.MultipleChoiceField()

    def __init__(self, *args, **kwargs):
        super(ImportRepositoryForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-import-repository'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.import_image')
        self.helper.help_text_inline = True
        self.fields['hosts'].choices = \
            [(x.id, x.name) for x in get_available_hosts()]

class ContainerForm(forms.Form):
    image = forms.ChoiceField()
    command = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(CreateContainerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-create-container'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.create_container')
        self.helper.help_text_inline = True
        self.fields['image'].widget.attrs['readonly'] = True

class ImageBuildForm(forms.Form):
    dockerfile = forms.FileField(required=False)
    url = forms.URLField(help_text='Dockerfile URL', required=False)
    tag = forms.CharField(help_text='i.e. app-v1', required=False)
    hosts = forms.MultipleChoiceField()

    def __init__(self, *args, **kwargs):
        super(ImageBuildForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-build-image'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_action = reverse('containers.views.build_image')
        self.helper.help_text_inline = True
        self.fields['hosts'].choices = \
            [(x.id, x.name) for x in get_available_hosts()]
