#!/usr/bin/env python

import check
from minio import Minio
from minio.error import S3Error


def main(args):
    # print(args)
    check.check_it(args)
    client = Minio(
        "minio-operator9000.minio-dev.svc.cluster.local:9000",
        access_key="AIUCaQb4Do9LEBvAPyxN",
        secret_key="XghVdcJnKpe3nH1n3fQMpOtxvz7Qz2Ua0E5DBRwE",
        secure=False
    )
    client.make_bucket("my-test-bucket")

    return args


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))