import tenseal as ts

from settings import POLY_MOD_DEGREE


def tensor_context():
    context = ts.context(
        ts.SCHEME_TYPE.BFV, poly_modulus_degree=POLY_MOD_DEGREE, plain_modulus=1032193
    )
    context.generate_galois_keys()
    context.generate_relin_keys()
    context.global_scale = 2**40
    return context
