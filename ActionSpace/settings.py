# coding=utf-8
"""
Django settings for ActionSpace project.

Generated by 'django-admin startproject' using Django 1.9.8.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

from __future__ import absolute_import
import os
import logging
import django.utils.log
import logging.handlers

USE_DJANGO_CELERY = False
USE_DEBUG_TOOLBAR = True
DEBUG_TOOLBAR_CHG_TAG = False
USE_ALL_AUTH = False
MQ_URL = 'amqp://action_space:action_space@localhost:5672/%2F'
USE_ORACLE = True
OM_ENV = 'UAT'

if USE_DJANGO_CELERY:
    import djcelery

    djcelery.setup_loader()
    BROKER_URL = 'django://'
    CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
    CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
else:
    # Celery setting#
    BROKER_URL = MQ_URL
    CELERY_RESULT_BACKEND = 'amqp'
    CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_TIMEZONE = 'Asia/Shanghai'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'p497&f@ey9wu33lc*)pa(ruj!58cq%=vfatufny6)y!u!))0f4'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# noinspection PyUnresolvedReferences
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(name)s:%(module)s:%(funcName)s:%(lineno)d] [%(levelname)s]:%(message)s'
        }

        # 日志格式
    },
    'filters': {
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        'default': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'om.log'),  # 日志输出文件
            'maxBytes': 1024 * 1024 * 5,  # 文件大小
            'backupCount': 5,  # 备份份数
            'formatter': 'standard',  # 使用哪种formatters日志格式
        },
        'error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        'om': {
            'handlers': ['default', 'console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

logger = logging.getLogger('om')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'ckeditor',
    'ckeditor_uploader',
    'django_extensions',
    'guardian',
    'rest_framework',
    # 'channels',
    'om.apps.OmConfig',
]

if USE_DEBUG_TOOLBAR:
    INSTALLED_APPS += ['template_profiler_panel', 'debug_toolbar']

if USE_DJANGO_CELERY:
    INSTALLED_APPS += ['djcelery', 'kombu.transport.django']

if USE_ALL_AUTH:
    INSTALLED_APPS += [
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        # ... include the providers you want to enable:
        'allauth.socialaccount.providers.amazon',
        'allauth.socialaccount.providers.angellist',
        'allauth.socialaccount.providers.asana',
        'allauth.socialaccount.providers.baidu',
        'allauth.socialaccount.providers.basecamp',
        'allauth.socialaccount.providers.bitbucket',
        'allauth.socialaccount.providers.bitbucket_oauth2',
        'allauth.socialaccount.providers.bitly',
        'allauth.socialaccount.providers.coinbase',
        'allauth.socialaccount.providers.digitalocean',
        'allauth.socialaccount.providers.douban',
        'allauth.socialaccount.providers.draugiem',
        'allauth.socialaccount.providers.dropbox',
        'allauth.socialaccount.providers.dropbox_oauth2',
        'allauth.socialaccount.providers.edmodo',
        'allauth.socialaccount.providers.eveonline',
        'allauth.socialaccount.providers.evernote',
        'allauth.socialaccount.providers.facebook',
        'allauth.socialaccount.providers.feedly',
        'allauth.socialaccount.providers.flickr',
        'allauth.socialaccount.providers.foursquare',
        'allauth.socialaccount.providers.fxa',
        'allauth.socialaccount.providers.github',
        'allauth.socialaccount.providers.gitlab',
        'allauth.socialaccount.providers.google',
        'allauth.socialaccount.providers.hubic',
        'allauth.socialaccount.providers.instagram',
        'allauth.socialaccount.providers.linkedin',
        'allauth.socialaccount.providers.linkedin_oauth2',
        'allauth.socialaccount.providers.mailru',
        'allauth.socialaccount.providers.odnoklassniki',
        'allauth.socialaccount.providers.openid',
        'allauth.socialaccount.providers.orcid',
        'allauth.socialaccount.providers.paypal',
        'allauth.socialaccount.providers.persona',
        'allauth.socialaccount.providers.pinterest',
        'allauth.socialaccount.providers.reddit',
        'allauth.socialaccount.providers.robinhood',
        'allauth.socialaccount.providers.shopify',
        'allauth.socialaccount.providers.slack',
        'allauth.socialaccount.providers.soundcloud',
        'allauth.socialaccount.providers.spotify',
        'allauth.socialaccount.providers.stackexchange',
        'allauth.socialaccount.providers.stripe',
        'allauth.socialaccount.providers.tumblr',
        'allauth.socialaccount.providers.twentythreeandme',
        'allauth.socialaccount.providers.twitch',
        'allauth.socialaccount.providers.twitter',
        'allauth.socialaccount.providers.untappd',
        'allauth.socialaccount.providers.vimeo',
        'allauth.socialaccount.providers.vk',
        'allauth.socialaccount.providers.weibo',
        'allauth.socialaccount.providers.weixin'
    ]

    SOCIALACCOUNT_PROVIDERS = {
        'weixin': {
            'AUTHORIZE_URL': 'https://open.weixin.qq.com/connect/oauth2/authorize',  # for media platform
        }
    }

    SITE_ID = 2

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAdminUser'
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    # 'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'PAGE_SIZE': 10,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination'
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # default
    'guardian.backends.ObjectPermissionBackend'
)

if USE_ALL_AUTH:
    AUTHENTICATION_BACKENDS += ('allauth.account.auth_backends.AuthenticationBackend',)

MIDDLEWARE_CLASSES = [
    #  'django.middleware.locale.LocaleMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.admindocs.middleware.XViewMiddleware'
]

if USE_DEBUG_TOOLBAR:
    MIDDLEWARE_CLASSES = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE_CLASSES

ROOT_URLCONF = 'ActionSpace.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

if USE_ALL_AUTH:
    TEMPLATES[0]['OPTIONS']['context_processors'] += ['django.template.context_processors.request']

WSGI_APPLICATION = 'ActionSpace.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

if USE_ORACLE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.oracle',
            'NAME': 'hsctmdb',
            'USER': 'omdata',
            'PASSWORD': 'Omdata1234'
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'zh-Hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = (os.path.join(BASE_DIR, 'templates', 'locale'),)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static').replace('\\', '/')
STATICFILES_DIRS = (
    ("om", os.path.join(STATIC_ROOT, 'om')),
    ("ckeditor", os.path.join(STATIC_ROOT, 'ckeditor')),
    ("admin", os.path.join(STATIC_ROOT, 'admin')),
)
STATIC_URL = '/static/'
# CKEDITOR_JQUERY_URL = '//ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js'
CKEDITOR_JQUERY_URL = '//cdn.bootcss.com/jquery/3.1.0/jquery.min.js'
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'JustifyLeft', 'JustifyCenter',
             'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source']
        ]
    },
    'awesome_ckeditor': {
        'toolbar': 'Full',
    }
}

#  LOGIN_URL = '/admin/login/'
LOGIN_URL = '/api-auth/login/'

CHANNEL_LAYERS = {
    'default': {
        # 'BACKEND': 'asgi_redis.RedisChannelLayer',
        'BACKEND': 'asgiref.inmemory.ChannelLayer',
        # 'CONFIG': {
        #     'hosts': [os.environ.get('REDIS_URL', 'redis://10.25.161.126:6382')],
        # },
        'ROUTING': 'ActionSpace.routing.channel_routing'
    }
}

if USE_DEBUG_TOOLBAR:
    DEBUG_TOOLBAR_PANELS = [
        'ddt_request_history.panels.request_history.RequestHistoryPanel',
        'template_profiler_panel.panels.template.TemplateProfilerPanel',
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ]

    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': 'ddt_request_history.panels.request_history.allow_ajax',
        'RESULTS_STORE_SIZE': 100,
        'JQUERY_URL': '//cdn.bootcss.com/jquery/3.1.0/jquery.min.js',
        'SHOW_COLLAPSED': True,
        'ENABLE_STACKTRACES': True,
        'SHOW_TEMPLATE_CONTEXT': True
    }

    if DEBUG_TOOLBAR_CHG_TAG:
        DEBUG_TOOLBAR_CONFIG = {
            'TAG': 'div',
        }

    INTERNAL_IPS = ('127.0.0.1',)
