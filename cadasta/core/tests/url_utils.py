from django.conf import settings

VERSION = settings.REST_FRAMEWORK.get('DEFAULT_VERSION')


def version_ns(ns):
    return'{v}:{ns}'.format(
        v=VERSION,
        ns=ns
    )


def version_url(url):
    return'/{v}{url}'.format(
        v=VERSION,
        url=url
    )
