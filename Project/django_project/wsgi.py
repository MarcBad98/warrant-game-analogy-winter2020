import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
application = get_wsgi_application()


"""


# raw WSGI code to temporarily take down the website
def application(environ, start_response):
    status = '200 OK'
    content = "Site down for maintenance"
    response_headers = [('Content-Type', 'text/html'), ('Content-Length', str(len(content)))]
    start_response(status, response_headers)
    yield content.encode('utf8')


"""
