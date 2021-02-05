import numpy as np
import casadi as cas
from aerosandbox.tools.string_formatting import stdout_redirected
from aerosandbox.optimization.opti import Opti
from typing import Union, Dict, Callable, List
from aerosandbox.optimization.math import *
from aerosandbox.modeling.surrogate_model import SurrogateModel
import copy
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(palette=sns.color_palette("husl", 2))


class FittedModel(SurrogateModel):
    """
    A model that is fitted to data. Maps from R^N -> R^1.

    You can evaluate this model at a given point by calling it just like a function, e.g.:

    >>> y = my_fitted_model(x)

    The input to the model (`x` in the example above) is of the type:
        * in the general N-dimensional case, a dictionary where keys are variable names and values are float/array
        * in the case of a 1-dimensional input (R^1 -> R^2), a float/array.
    If you're not sure what the input type of `my_fitted_model` should be, just do:

    >>> print(my_fitted_model) # Displays the valid input type to the model

    The output of the model (`y` in the example above) is always a float or array.

    Created as the output of the `fit_model()` function; look at the docstring of that function for further
    documentation.
    """

    def __init__(self,
                 model: Callable[
                     [
                         Union[np.ndarray, Dict[str, np.ndarray]],
                         Dict[str, float]
                     ],
                     np.ndarray
                 ],
                 parameters: Dict[str, float],
                 x_data: Union[np.ndarray, Dict[str, np.ndarray]],
                 y_data: np.ndarray,
                 ):
        super().__init__()
        self.model = model
        self.parameters = parameters
        self.x_data = x_data
        self.y_data = y_data

    def __call__(self, x):
        return self.model(x, self.parameters)

    def __repr__(self) -> str:
        input_names = self.input_names()
        if input_names is not None:
            input_description = f"a dict with keys {input_names}; values as float or array"
        else:
            input_description = f"a float or array"
        return "\n".join([
            f"FittedModel(x) [R^{self.input_dimensionality()} -> R^1]",
            f"\tInput: {input_description}"
        ])

    def input_dimensionality(self) -> int:
        input_names = self.input_names()
        if input_names is not None:
            return len(input_names)
        else:
            return 1

    def input_names(self) -> Union[List, None]:
        try:
            return list(self.x_data.keys())
        except AttributeError:
            return None

    def plot_fit(self, resolution=100):
        def axis_range(x_data_axis: np.ndarray) -> Tuple[float, float]:
            """
            Given the entries of one axis of the dependent variable, determine a min/max range over which to plot the fit.
            Args:
                x_data_axis: The entries of one axis of the dependent variable, i.e. x_data["x1"].

            Returns: A tuple representing the (min, max) value over which to plot that axis.
            """
            minval = np.min(x_data_axis)
            maxval = np.max(x_data_axis)

            return (minval, maxval)

        if self.input_dimensionality() == 1:

            ### Parse the x_data
            if self.input_names() is not None:
                x_name = self.x_data.keys()[0]
                x_data = self.x_data.values()[0]

                minval, maxval = axis_range(x_data)

                x_fit = {x_name: linspace(minval, maxval, resolution)}
                y_fit = self(x_fit)
            else:
                x_name = "x"
                x_data = self.x_data

                minval, maxval = axis_range(x_data)

                x_fit = linspace(minval, maxval, resolution)
                y_fit = self(x_fit)

            ### Plot the 2D figure
            fig = plt.figure(dpi=200)
            plt.plot(
                x_data,
                self.y_data,
                ".",
                label="Data",
            )
            plt.plot(
                x_fit,
                y_fit,
                "-",
                label="Fit",
                zorder=4,
            )
            plt.xlabel(x_name)
            plt.ylabel(rf"$f({x_name})$")
            plt.title(r"Fit of FittedModel")
            plt.tight_layout()
            plt.legend()
            plt.show()


def fit_model(
        model: Callable[
            [
                Union[np.ndarray, Dict[str, np.ndarray]],
                Dict[str, float]
            ],
            np.ndarray
        ],
        x_data: Union[np.ndarray, Dict[str, np.ndarray]],
        y_data: np.ndarray,
        parameter_guesses: Dict[str, float],
        parameter_bounds: Dict[str, tuple] = None,
        residual_norm_type: str = "L2",
        fit_type: str = "best",
        weights: np.ndarray = None,
        put_residuals_in_logspace: bool = False,
) -> FittedModel:
    """
    Fits an analytical model to n-dimensional data using an automatic-differentiable optimization approach.

    Args:

        model: The model that you want to fit your dataset to. This is a callable with syntax f(x, p) where:

            * x is a dict of dependent variables. Same format as x_data [dict of 1D ndarrays of length n].

                * If the model is one-dimensional (e.g. f(x1) instead of f(x1, x2, x3...)), you can instead interpret x
                as a 1D ndarray. (If you do this, just give `x_data` as an array.)

            * p is a dict of parameters. Same format as param_guesses [dict with syntax param_name:param_value].

            Model should return a 1D ndarray of length n.

            Basically, if you've done it right:
            >>> model(x_data, parameter_guesses)
            should evaluate to a 1D ndarray where each x_data is mapped to something analogous to y_data. (The fit
            will likely be bad at this point, because we haven't yet optimized on param_guesses - but the types
            should be happy.)

            Model should use simple operators where possible (+,-,*,/,**), NumPy operators for more complex things (
            np.exp(), np.log(), np.fabs()), and aerosandbox.optimization.math operators for even more complex things
            (if_else(), array() for new arrays, etc.).

        x_data: Values of the dependent variable(s) in the dataset to be fitted. This is a dictionary; syntax is {
        var_name:var_data}.

            * If the model is one-dimensional (e.g. f(x1) instead of f(x1, x2, x3...)), you can instead supply x_data
            as a 1D ndarray. (If you do this, just treat `x` as an array in your model, not a dict.)

        y_data: Values of the independent variable in the dataset to be fitted. [1D ndarray of length n]

        parameter_guesses: a dict of fit parameters. Syntax is {param_name:param_initial_guess}.

            * Parameters will be initialized to the values set here; all parameters need an initial guess.

            * param_initial_guess is a float; note that only scalar parameters are allowed.

        parameter_bounds: Optional: a dict of bounds on fit parameters. Syntax is {param_name:(min, max)}.

            * May contain only a subset of param_guesses if desired.

            * Use None to represent one-sided constraints (i.e. (None, 5)).

        residual_norm_type: What error norm should we minimize to optimize the fit parameters? Options:

            * "L1": minimize the L1 norm or sum(abs(error)). Less sensitive to outliers.

            * "L2": minimize the L2 norm, also known as the Euclidian norm, or sqrt(sum(error ** 2)). The default.

            * "Linf": minimize the L_infinty norm or max(abs(error)). More sensitive to outliers.

        fit_type: Should we find the model of best fit (i.e. the model that minimizes the specified residual norm),
        or should we look for a model that represents an upper/lower bound on the data (useful for robust surrogate
        modeling, so that you can put bounds on modeling error):

            * "best": finds the model of best fit. Usually, this is what you want.

            * "upper bound": finds a model that represents an upper bound on the data (while still trying to minimize
            the specified residual norm).

            * "lower bound": finds a model that represents a lower bound on the data (while still trying to minimize
            the specified residual norm).

        weights: Optional: weights for data points. If not supplied, weights are assumed to be uniform.

            * Weights are automatically normalized. [1D ndarray of length n]

        put_residuals_in_logspace: Whether to optimize using the logarithmic error as opposed to the absolute error
        (useful for minimizing percent error).

        Note: If any model outputs or data are negative, this will raise an error!

    Returns: A model in the form of a FittedModel object. Some things you can do:
        >>> y = FittedModel(x) # evaluate the FittedModel at new x points
        >>> FittedModel.parameters # directly examine the optimal values of the parameters that were found
        >>> FittedModel.plot_fit() # plot the fit


    """

    ##### Prepare all inputs, check types/sizes.

    ### Flatten all inputs
    def flatten(input):
        return np.array(input).flatten()

    try:
        x_data = {
            k: flatten(v)
            for k, v in x_data.items()
        }
        x_data_is_dict = True
    except AttributeError:  # If it's not a dict or dict-like, assume it's a 1D ndarray dataset
        x_data = flatten(x_data)
        x_data_is_dict = False
    y_data = flatten(y_data)
    n_datapoints = length(y_data)

    ### Handle weighting
    if weights is None:
        weights = np.ones(n_datapoints)
    else:
        weights = flatten(weights)
    weights /= sum1(weights)  # Normalize weights so that they sum to 1.

    ### Check format of parameter_bounds input
    if parameter_bounds is None:
        parameter_bounds = {}
    for param_name, v in parameter_bounds.items():
        if param_name not in parameter_guesses.keys():
            raise ValueError(
                f"A parameter name (key = \"{param_name}\") in parameter_bounds was not found in parameter_guesses.")
        if not length(v) == 2:
            raise ValueError(
                "Every value in parameter_bounds must be a tuple in the format (lower_bound, upper_bound). "
                "For one-sided bounds, use None for the unbounded side.")

    ### If putting residuals in logspace, check positivity
    if put_residuals_in_logspace:
        if not np.all(y_data > 0):
            raise ValueError("You can't fit a model with residuals in logspace if y_data is not entirely positive!")

    ### Check dimensionality of inputs to fitting algorithm
    relevant_inputs = {
        "y_data" : y_data,
        "weights": weights,
    }
    try:
        relevant_inputs.update(x_data)
    except TypeError:
        relevant_inputs.update({"x_data": x_data})

    for key, value in relevant_inputs.items():
        # Check that the length of the inputs are consistent
        series_length = length(value)
        if not series_length == n_datapoints:
            raise ValueError(
                f"The supplied data series \"{key}\" has length {series_length}, but y_data has length {n_datapoints}.")

    ##### Formulate and solve the fitting optimization problem

    ### Initialize an optimization environment
    opti = Opti()

    ### Initialize the parameters as optimization variables
    params = {}
    for param_name, param_initial_guess in parameter_guesses.items():
        if param_name in parameter_bounds:
            params[param_name] = opti.variable(
                init_guess=param_initial_guess,
                lower_bound=parameter_bounds[param_name][0],
                upper_bound=parameter_bounds[param_name][1],
            )
        else:
            params[param_name] = opti.variable(
                init_guess=param_initial_guess,
            )

    ### Evaluate the model at the data points you're trying to fit
    y_model = model(x_data, params)
    if y_model is None:  # Make sure that y_model actually returned something sensible
        raise TypeError("model(x_data, parameter_guesses) returned None, when it should've returned a 1D ndarray.")

    ### Compute how far off you are (error)
    if not put_residuals_in_logspace:
        error = y_model - y_data
    else:
        y_model = np.fmax(y_model, 1e-300)  # Keep y_model very slightly always positive, so that log() doesn't NaN.
        error = np.log(y_model) - np.log(y_data)

    ### Set up the optimization problem to minimize some norm(error), which looks different depending on the norm used:
    if residual_norm_type.lower() == "l1":  # Minimize the L1 norm
        abs_error = opti.variable(init_guess=0,
                                  n_vars=length(y_data))  # Make the abs() of each error entry an opt. var.
        opti.subject_to([
            abs_error >= error,
            abs_error >= -error,
        ])
        opti.minimize(sum1(abs_error))

    elif residual_norm_type.lower() == "l2":  # Minimize the L2 norm
        opti.minimize(sum1(error ** 2))

    elif residual_norm_type.lower() == "linf":  # Minimize the L-infinity norm
        linf_value = opti.variable(init_guess=0)  # Make the value of the L-infinity norm an optimization variable
        opti.subject_to([
            linf_value >= error,
            linf_value >= -error
        ])
        opti.minimize(linf_value)

    else:
        raise ValueError("Bad input for the 'residual_type' parameter.")

    ### Add in the constraints specified by fit_type, which force the model to stay above / below the data points.
    if fit_type == "best":
        pass
    elif fit_type == "upper bound":
        opti.subject_to(y_model >= y_data)
    elif fit_type == "lower bound":
        opti.subject_to(y_model <= y_data)
    else:
        raise ValueError("Bad input for the 'fit_type' parameter.")

    ### Solve
    sol = opti.solve()

    ##### Construct a FittedModel

    ### Create a vector of solved parameters
    params_solved = {}
    for param_name in params:
        try:
            params_solved[param_name] = sol.value(params[param_name])
        except:
            params_solved[param_name] = np.NaN

    ### Return
    return FittedModel(
        model=model,
        parameters=params_solved,
        x_data=x_data,
        y_data=y_data,
    )