Django Vendor
=============

Django App Toolkit for selling digital and physical goods online.


Goals of the project:
- Drop in to existing Django Sites without requiring changes to how Django works (flow, not fight)
- Handle everything from the point of starting a purchase, until payment is complete.
- BYOPM, Bring Your Own Product Model.  Subclass your Product Model off of our base model and add whatever you want.  You are responsible for things like Catalogs and Presenting products to the user, we handle the purchasing of the products and generate a reciept you can look for.


For Developers
--------------

*NOTE: It is reconmended that you first setup a virtual environment.*

To install the project, all you need to do is check out the project and run the following to install all the dependencies:

```bash
pip install -r requirements.txt
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
