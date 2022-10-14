import logging

logger = logging.getLogger(__name__)


class StripeQueryBuilder:
    """
    Query builder that adheres to Stripe search rules found here https://stripe.com/docs/search

    Ex:
    To generate a query like 'name:"Johns Offer" AND metadata["site"]:"site4"'

    query_builder = StripeQueryBuilder()

    name_clause = query_builder.make_clause_template()
    name_clause['field'] = 'name'
    name_clause['value'] = 'Johns Offer'
    name_clause['operator'] = query_builder.EXACT_MATCH
    name_clause['next_operator'] = query_builder.AND

    metadata_clause = query_builder.make_clause_template()
    metadata_clause['field'] = 'metadata'
    metadata_clause['key'] = 'site'
    metadata_clause['value'] = 'site4'
    metadata_clause['operator'] = query_builder.EXACT_MATCH

    query = query_builder.build_search_query(processor.stripe.Product, [name_clause, metadata_clause])


    """

    # Search syntax
    EXACT_MATCH = ':'
    AND = 'AND'
    OR = 'OR'
    EXCLUDE = '-'
    NULL = 'NULL'
    SUBSTRING_MATCH = '~'
    GREATER_THAN = '>'
    LESS_THAN = '<'
    EQUALS = '='
    GREATER_THAN_OR_EQUAL_TO = '>='
    LESS_THAN_OR_EQUAL_TO = '<='

    # Valid fields
    VALID_FIELDS = {
        'charge': [
            'amount',
            'billing_details.address.postal_code',
            'created',
            'currency',
            'customer',
            'disputed',
            'metadata',
            'payment_method_details.card.last4',
            'payment_method_details.card.exp_month',
            'payment_method_details.card.exp_year',
            'payment_method_details.card.brand',
            'payment_method_details.card.fingerprint',
            'refunded',
            'status'
        ],
        'customer': [
            'created',
            'email',
            'metadata',
            'name',
            'phone'
        ],
        'invoice': [
            'created',
            'currency',
            'customer',
            'metadata',
            'number',
            'receipt_number',
            'subscription',
            'total'
        ],
        'paymentintent': [
            'amount',
            'created',
            'currency',
            'customer',
            'metadata',
            'status',
        ],
        'price': [
            'active',
            'lookup_key',
            'currency',
            'product',
            'metadata',
            'type',
        ],
        'product': [
            'active',
            'description',
            'name',
            'shippable',
            'metadata',
            'url',
        ],
        'subscription': [
            'created',
            'metadata',
            'status',
        ],
    }

    def make_clause_template(self, field=None, operator=None, key=None, value=None, next_operator=None):
        return {
            'field': field,
            'operator': operator,
            'key': key,
            'value': value,
            'next_operator': next_operator
        }

    def is_valid_field(self, stripe_object_class, field):
        return field in self.VALID_FIELDS[stripe_object_class.__name__.lower()]

    def search_clause_checks_pass(self, clause_obj):
        """
        All checks should be added here to make sure the caller isnt missing required params
        """
        if clause_obj.get('field', None) == 'metadata':
            if not clause_obj.get('key', None):
                logger.error(f'StripeQueryBuilder.search_clause_checks_pass: metadata searches need a key field')
                return False

        # TODO add more checks

        return True

    def build_search_query(self, stripe_object_class, search_clauses):
        if not isinstance(search_clauses, list):
            logger.info(f'Passed in params {search_clauses} is not a list of dicts')
            return None

        if not len(search_clauses) > 0:
            logger.info(f'Passed in params {search_clauses} cannot be empty')
            return None

        query = ""
        for index, query_obj in enumerate(search_clauses):
            field = query_obj.get('field', None)
            operator = query_obj.get('operator', None)
            key = query_obj.get('key', None)
            value = query_obj.get('value', None)
            next_operator = query_obj.get('next_operator', None)

            if not self.search_clause_checks_pass(query_obj):
                logger.error(f'StripeQueryBuilder.build_search_query: search clause {query_obj} is not valid')
                return query

            if self.is_valid_field(stripe_object_class, field):
                if not key:
                    # not metadata
                    if isinstance(value, str):
                        query += f'{field}{operator}"{value}"'
                    else:
                        query += f'{field}{operator}{value}'
                else:
                    # is metadata
                    if isinstance(value, str):
                        query += f'{field}["{key}"]{operator}"{value}"'
                    else:
                        query += f'{field}["{key}"]{operator}{value}'

                if next_operator:
                    # space, AND, OR
                    query += f' {next_operator} '

            else:
                logger.error(f'StripeQueryBuilder.build_search_query: {field} is not valid for {stripe_object_class}')
                return query

        return query
