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
    PRICE    = ('price', 'Price')
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
    elif object_name == StripeObjects.PRICE:
        return stripe.Price
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

def object_data_has_site_in_metadata(object_data):
    if 'metadata' not in object_data:
        return False
    
    if 'site' not in object_data['metadata']:
        return False

    return True

def crud_stripe_object(crud_action, stripe_object_name, stripe_object_id=None, **kwargs):
    stripe_object = get_stripe_object(stripe_object_name)

    if crud_action is not CRUDChoices.DELETE:
        if not object_data_has_site_in_metadata(kwargs):
            raise TypeError(f"Object data does not have site key value in metadata attribute")

    return execute_crud(crud_action, stripe_object, stripe_object_id, **kwargs) 
