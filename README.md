![Django Vendor CI](https://github.com/renderbox/django-vendor/workflows/Django%20Vendor%20CI/badge.svg?branch=master)

![Django Vendor Develop](https://github.com/renderbox/django-vendor/workflows/Django%20Vendor%20Develop/badge.svg?branch=develop)

[![Documentation Status](https://readthedocs.org/projects/django-vendor/badge/?version=latest)](https://django-vendor.readthedocs.io/en/latest/?badge=latest)

# Django Vendor

Django App Toolkit for selling digital and physical goods online.

The philosophy is "Cart to Receipt".  What you put in the cart and what you do after the purchase is up to you.  The app is opinionated within scope.

Goals of the project:
- Drop in to existing Django Sites without requiring changes to how Django works (flow, not fight)
- Handle everything from the point of starting a purchase, until payment is complete.
- BYOPM, Bring Your Own Product Model.  Subclass your Product Model off of our base model and add whatever you want.  You are responsible for things like Catalogs and Presenting products to the user, we handle the purchasing of the products and generate a receipt you can look for.


## For Developers

*NOTE: It is reconmended that you first setup a virtual environment.*

To install the project, all you need to do is check out the project and run the following to install all the dependencies:

```bash
pip install -r requirements.txt
```

For developers, you'll need to also include a couple of dependencies that are only used in develop mode.  Run this from the root level of the project.

```bash
pip install -e .[dev, authorizenet]
```

To run the project, go into the develop folder:

To setup the models:

```bash
./manage.py migrate
```


Create the Super user

```bash
./manage.py createsuperuser
```


Then load the developer fixture if you want to pre-populate the cart & catalog

```bash
./manage.py loaddata developer
```

To run the project:

```bash
./manage.py runserver
```


to dump unit test data

```bash
./manage.py dumpdata --indent 4 auth.group --natural-foreign --natural-primary > fixtures/group.json
./manage.py dumpdata --indent 4 auth.user --natural-foreign > fixtures/user.json
./manage.py dumpdata --indent 4 -e contenttypes -e auth.permission -e sessions -e admin.logentry -e account.emailaddress -e auth.group -e auth.user > fixtures/unit_test.json
```



The install process
1) Add the app to your project
2) Create your Product model that inherits from the ProductModelBase base class.
3) Change the settings.py value for VENDOR_PRODUCT_MODEL to point to your model
4) Make migrations
5) Migrate

