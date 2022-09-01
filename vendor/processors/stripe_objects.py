import stripe

from django.db.models import TextChoices
# from vendor.models import CustomerProfile, Offer, Invoice, Subscription

stripe.api_key = "sk_test_51LYCNjJHHVfmV6EHPwkh9bogbRyTQFoiGV85yUrQyPFyur3BI2Rjtkhi7XCCNIsPvzOlYTVjzOYmljHPe1X2caIr00uVSfVkmn"



class StripeObjects(TextChoices):
    COUPON   = ('coupon', 'Coupon')
    CUSTOMER = ('customer', 'Customer')
    DISCOUNT = ('discount', 'Discount')
    INVOICE  = ('invoice', 'Invoice')
    PRODUCT  = ('product', 'Product')
    SUBSCRIPTION = ('subscription', 'Subscription')


class CRUDChoices(TextChoices):
    CREATE  = ('create', 'create')
    RETIEVE = ('retrieve', 'retrieve')
    UPDATE  = ('update', 'update')
    DELETE  = ('delete', 'delete')


def set_stripe_object_id(object_name, id):
    return {object_name: id}

def get_stripe_object_id(object_name, meta_field):
    return meta_field[object_name]

def get_stripe_object(object_name):
    if object_name == StripeObjects.COUPON:
        return stripe.Coupon
    elif object_name == StripeObjects.CUSTOMER:
        return stripe.Customer
    elif object_name == StripeObjects.DISCOUNT:
        return stripe.Discount
    elif object_name == StripeObjects.INVOICE:
        return stripe.Invoice
    elif object_name == StripeObjects.PRODUCT:
        return stripe.Product
    elif object_name == StripeObjects.SUBSCRIPTION:
        return stripe.Subscription
    else:
        raise TypeError(f"Stripe Object: {object_name} is not supported")

def execute_crud(crud_action, stripe_object, stripe_id=None, **kwargs):
    if crud_action == CRUDChoices.CREATE:
        return stripe_object.create(**kwargs)

    elif crud_action == CRUDChoices.RETIEVE:
        return stripe_object.search(**kwargs)

    elif crud_action == CRUDChoices.DELETE:
        return stripe_object.delete(stripe_id)

    elif curd_action == CRUDChoices.UPDATE:
        return stripe_object.modify(stripe_id, **kwargs)

    else:
        raise TypeError(f"CRUD action: {crud_action} is not valid")


def crud_stripe_object(crud_action, stripe_object_name, stripe_object_id=None, **kwrgs):
    stripe_object = get_stripe_object(stripe_object_name)

    return execute_crud(crud_action, stripe_object, stripe_object_id, **kwrgs) 

def create_customer(email, name, address=None, description=None, metadata=None):
    return stripe.Customer.create(
        email=email,
        name=name,
        address=address,
        description=description,
        metadata=metadata
    )

c1 = {
    'name': "Norrin Radd",
    'email': 'norrin@radd.com'
}

c2 = {
    'name': "Norrin Radd",
    'email': 'norrin@radd.com',
    'address': {
        'city': "na",
        'country': "US",
        'line1': "Salvatierra walk",
        'postal_code': "90321",
        'state': 'CA'
    },
}
p1 = {
    'name': "Monthly Subscription"
}
p2 = {
    "name": "Annual Subscription",
    'metadata': {
        'site': 'Sound Collective'
    }
}

customer_1 = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.CUSTOMER, **c1)
monthly_license = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **p1)
annual_license = crud_stripe_object(CRUDChoices.CREATE, StripeObjects.PRODUCT, **p2)

print(customer_1)
print(monthly_license)
print(annual_license)


print(f"customer 1 id: {customer_1.id}")