from django import template
from django.template.defaultfilters import stringfilter
from django.utils.translation import ugettext as _
from hosts.models import Host
from datetime import datetime

register = template.Library()

@register.filter
def container_status(value):
    """
    Returns container status as a bootstrap class

    """
    cls = ''
    if value:
        if value.get('Running'):
            cls = 'success'
        elif value.get('ExitCode') == 0:
            cls = 'info'
        else:
            cls = 'important'
    return cls

@register.filter
def container_uptime(value):
    """
    Returns container uptime from date stamp

    """
    if value:
        try:
            tz = value.split('.')[-1]
            ts = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.' + tz)
            return datetime.utcnow().replace(microsecond=0) - ts
        except:
            return ''
    return value

@register.filter
def container_port_link(port, host):
    """
    Returns container port as link

    :param port: Container port
    :param host: Container host name

    """
    ret = port
    if port:
        host = Host.objects.get(name=host)
        host_url = host.hostname
        if 'unix' in host.hostname:
            host_url = '127.0.0.1'
        link = '<a href="http://{0}:{1}" target="_blank">{1}</a>'.format(
            host_url, port)
        ret = link
    return ret

@register.filter
def container_host_url(interface, hostname):
    """
    Returns exposed interface URL, replacing default 0.0.0.0
    with container hostname as url

    :param interface: Port interface
    :param hostname: Container host name

    """
    if interface == '0.0.0.0':
        if 'unix' in hostname:
            host_url = '127.0.0.1'
        else:
            host_url = hostname
    else:
        host_url = interface
    return 'http://{0}'.format(host_url)

@register.filter
@stringfilter
def format_name(value):
    """
    Return container name without slash '/'
    """
    if not value:
        return value

    return value.replace("/", "")

@register.filter
@stringfilter
def container_memory_to_mb(value):
    """
    Returns container memory as MB
    """

    if value.strip():
        value = float(value.strip())
        if int(value) != 0:
            return '{0} MB'.format(int(value) / 1048576)
        else:
            return _('unlimited')

@register.filter
@stringfilter
def container_cpu_set(value):
    """
    Returns container cpu set
    """

    string = ""

    if value.strip() and len(value.split("-")) == 2:
        array = value.split("-")
        
        start = int(array[0])
        end = int(array[1])

        if start == 0 and end == 3:
            string = "0, 1, 2, 3"
        elif start == 4 and end == 7:
            string = "4, 5, 6, 7"
    elif value.strip() and len(value.split(',')) == 2:
        array = value.split(",")
        string = array[0] + " and " + array[1]

    return string
@register.filter
@stringfilter
def container_cpu(value):
    """
    Returns container memory as MB
    """

    if value.strip() and int(value) != 0:
        return '{}%'.format(value)
    else:
        return _('unlimited')

@register.filter()
def split(value, arg):
    return value.split(arg)

@register.filter()
def get_short_id(value):
    return value[:12]
