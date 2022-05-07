#! /bin/bash

set -e

TAG=$1

SCRIPT=$(readlink -f $0)
SCRIPTPATH=`dirname $SCRIPT`

if [ -z "$TAG" ]; then
    SHA=`git rev-parse --short HEAD`
    TAG="sha-$SHA"
    echo "No image tag specified, using HEAD: $TAG"
fi

IMAGE=ghcr.io/michaelvl/istio-katas

DIGEST=$($SCRIPTPATH/../scripts/skopeo.sh inspect docker://$IMAGE:$TAG | jq -r .Digest)
echo "Using digest: $DIGEST"

#IMAGE_TAG=":$TAG"
IMAGE_TAG="@$DIGEST"

FILES=""

for m in `find deploy -name '*.yaml'`; do
    echo "Updating $m"
    sed -i -E "s#(^\s+-\s+image\:\s+$IMAGE)[\:@]{1}.*#\1$IMAGE_TAG#" $m
    FILES="$FILES $m"
done

echo $FILES > _tmp_image_tag_update
echo "Updated file list saved in _tmp_image_tag_update"
