"""
Testing the Intravoxel incoherent motion module

The values of the various parameters used in the tests are inspired by
the study of the IVIM model applied to MR images of the brain by
Federau, Christian, et al. [1].

References
----------
.. [1] Federau, Christian, et al. "Quantitative measurement
       of brain perfusion with intravoxel incoherent motion
       MR imaging." Radiology 265.3 (2012): 874-881.
"""
import numpy as np
from numpy.testing import (assert_array_equal, assert_array_almost_equal,
                           assert_raises)

from dipy.reconst.ivim import ivim_function, IvimModel
from dipy.core.gradients import gradient_table, generate_bvecs
from dipy.sims.voxel import multi_tensor

from distutils.version import LooseVersion
import scipy

SCIPY_VERSION = LooseVersion(scipy.version.short_version)


def test_single_voxel_fit():
    """
    Test the implementation of the fitting for a single voxel.

    Here, we will use the multi_tensor function to generate a
    biexponential signal. The multi_tensor generates a multi
    tensor signal and expects eigenvalues of each tensor in mevals.
    Our basic test requires a scalar signal isotropic signal and
    hence we set the same eigenvalue in all three directions to
    generate the required signal.

    The bvals, f, D_star and D are inspired from the paper by
    Federau, Christian, et al. We use the function "generate_bvecs"
    to simulate bvectors corresponding to the bvalues.

    In the two stage fitting routine, initially we fit the signal
    values for bvals less than the specified split_b using the
    TensorModel and get an intial guess for f and D. Then, using
    these parameters we fit the entire data for all bvalues.
    """
    bvals = np.array([0., 10., 20., 30., 40., 60., 80., 100.,
                      120., 140., 160., 180., 200., 220., 240.,
                      260., 280., 300., 350., 400., 500., 600.,
                      700., 800., 900., 1000.])
    N = len(bvals)
    bvecs = generate_bvecs(N)
    gtab = gradient_table(bvals, bvecs.T)

    S0, f, D_star, D = 1.0, 0.132, 0.00885, 0.000921

    mevals = np.array(([D_star, D_star, D_star], [D, D, D]))
    # This gives an isotropic signal

    signal = multi_tensor(gtab, mevals, snr=None, S0=S0,
                          fractions=[f * 100, 100 * (1 - f)])
    data = signal[0]
    ivim_model = IvimModel(gtab)
    ivim_fit = ivim_model.fit(data)

    est_signal = ivim_function(ivim_fit.model_params, bvals)

    assert_array_equal(est_signal.shape, data.shape)
    assert_array_almost_equal(est_signal, data)
    assert_array_almost_equal(ivim_fit.model_params, [S0, f, D_star, D])
    # Test mask
    assert_raises(ValueError, ivim_model.fit,
                  np.ones((10, 10, 3)), np.ones((3, 3)))


def test_multivoxel():
    """Test fitting with multivoxel data.

    We generate a multivoxel signal to test the fitting for multivoxel data.
    This is to ensure that the fitting routine takes care of signals packed as
    1D, 2D or 3D arrays.
    """
    bvals = np.array([0., 10., 20., 30., 40., 60., 80., 100.,
                      120., 140., 160., 180., 200., 220., 240.,
                      260., 280., 300., 350., 400., 500., 600.,
                      700., 800., 900., 1000.])
    N = len(bvals)
    bvecs = generate_bvecs(N)
    gtab = gradient_table(bvals, bvecs.T)
    params = np.array([[1.0, 0.2052, 0.00473, 0.00066],
                       [101.0, 0.132, 0.00885, 0.000921]])

    data = np.empty((params.shape[0], N))
    for i in range(len(params)):
        data[i] = ivim_function(params[i], gtab.bvals)

    ivim_model = IvimModel(gtab, x0=[1, 0.02, 0.002, 0.0002])

    ivim_fit = ivim_model.fit(data)
    est_signal = np.empty((ivim_fit.model_params.shape[0], N))
    for i in range(len(ivim_fit.model_params)):
        est_signal[i] = ivim_function(ivim_fit.model_params[i], gtab.bvals)

    assert_array_equal(est_signal.shape, data.shape)
    assert_array_almost_equal(est_signal, data)
    assert_array_almost_equal(ivim_fit.model_params, params)


def test_predict():
    """
    Test model prediction API.

    The fit class has a predict method which can be used to
    generate the predicted signal from the parameters obtained
    after a fit. This test ensures that the predict method gives
    the required signal for simulated data.
    """
    bvals = np.array([0., 10., 20., 30., 40., 60., 80., 100.,
                      120., 140., 160., 180., 200., 220., 240.,
                      260., 280., 300., 350., 400., 500., 600.,
                      700., 800., 900., 1000.])
    N = len(bvals)
    bvecs = generate_bvecs(N)
    gtab = gradient_table(bvals, bvecs.T)

    S0, f, D_star, D = 1.0, 0.132, 0.00885, 0.000921

    mevals = np.array(([D_star, D_star, D_star], [D, D, D]))
    # This gives an isotropic signal

    signal = multi_tensor(gtab, mevals, snr=None, S0=S0,
                          fractions=[f * 100, 100 * (1 - f)])
    data = signal[0]
    ivim_model = IvimModel(gtab)
    ivim_fit = ivim_model.fit(data)

    p = ivim_fit.predict(gtab)
    assert_array_equal(p.shape, data.shape)
    assert_array_almost_equal(p, data)


def test_ivim_errors():
    """
    Test if errors raised in the module are working correctly.

    Scipy introduced bounded least squares fitting in the version 0.17
    and is not supported by the older versions. Initializing an IvimModel
    with bounds for older Scipy versions should raise an error.
    """
    bvals = np.array([0., 10., 20., 30., 40., 60., 80., 100.,
                      120., 140., 160., 180., 200., 220., 240.,
                      260., 280., 300., 350., 400., 500., 600.,
                      700., 800., 900., 1000.])
    N = len(bvals)
    bvecs = generate_bvecs(N)
    gtab = gradient_table(bvals, bvecs.T)

    # Run the test for Scipy versions less than 0.17
    if SCIPY_VERSION < '0.17':
        assert_raises(ValueError, IvimModel, gtab,
                      bounds=([0., 0., 0., 0.], [np.inf, 1., 1., 1.]))
    else:
        ivim_model = IvimModel(gtab,
                               bounds=([0., 0., 0., 0.], [np.inf, 1., 1., 1.]))
    # Check min signal
    assert_raises(ValueError, IvimModel, gtab, min_signal=-1)
