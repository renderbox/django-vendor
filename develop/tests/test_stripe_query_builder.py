from vendor.processors.stripe import StripeQueryBuilder


def test_build_search_query_happy_path_metadata_and_name():
    Product = type("Product", (), {})
    qb = StripeQueryBuilder()
    name_clause = qb.make_clause_template(
        field="name",
        value="Test Product",
        operator=qb.EXACT_MATCH,
        next_operator=qb.AND,
    )
    metadata_clause = qb.make_clause_template(
        field="metadata",
        key="site",
        value="example",
        operator=qb.EXACT_MATCH,
    )

    query = qb.build_search_query(Product, [name_clause, metadata_clause])

    assert query == 'name:"Test Product" AND metadata["site"]:"example"'


def test_build_search_query_requires_metadata_key():
    Product = type("Product", (), {})
    qb = StripeQueryBuilder()
    metadata_clause = qb.make_clause_template(
        field="metadata",
        value="missing_key",
        operator=qb.EXACT_MATCH,
    )

    query = qb.build_search_query(Product, [metadata_clause])

    assert query == ""


def test_build_search_query_rejects_invalid_field():
    Product = type("Product", (), {})
    qb = StripeQueryBuilder()
    bad_clause = qb.make_clause_template(
        field="not_valid",
        value="x",
        operator=qb.EXACT_MATCH,
    )

    query = qb.build_search_query(Product, [bad_clause])

    assert query == ""


def test_build_search_query_handles_numeric_values():
    Product = type("Product", (), {})
    qb = StripeQueryBuilder()
    clause = qb.make_clause_template(
        field="metadata",
        key="pk",
        value=42,
        operator=qb.EQUALS,
    )

    query = qb.build_search_query(Product, [clause])

    assert query == 'metadata["pk"]=42'
