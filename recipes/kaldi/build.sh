#! /usr/bin/env bash

pushd src || exit 1
./configure --shared --mathlib=OPENBLAS --openblas-root=${PREFIX} || exit 1
make util FSTROOT=blerg -j ${CPU_COUNT} || exit 1

if [ -d "${PKG_CONFIG_PATH}" ]; then
  make kaldi_cxxflags FSTROOT=blerg || exit 1
  make kaldi_ldflags FSTROOT=blerg || exit 1
  make kaldi_ldlibs FSTROOT=blerg || exit 1
  cat kaldi_cxxflags
  $PYTHON $RECIPE_DIR/build_pkg_config_file.py \
    kaldi_cxxflags kaldi_ldflags kaldi_ldlibs "${PKG_CONFIG_PATH}" \
    "${PREFIX}" "${PKG_VERSION}" || exit 1
fi

# kaldi builds in place. Move those foos into the build location.
# Conda should handle rpath 
for d in matrix util thread base; do
  mkdir -p ${PREFIX}/include/kaldi/$d || exit 1
  cp $d/*.h ${PREFIX}/include/kaldi/$d/ || exit 1
  cp $d/*.dylib ${PREFIX}/lib/ || cp $d/*.so ${PREFIX}/lib/ || exit 1
done

popd
