import matplotlib.pyplot as plt
import aerosandbox.numpy as np
from typing import Union

def wagners_function(reduced_time: Union[np.ndarray,float]):
    """ 
    A commonly used approximation to Wagner's function 
    (Jones, R.T. The Unsteady Lift of a Finite Wing; Technical Report NACA TN-682; NACA: Washington, DC, USA, 1939)
    
    Args:
        reduced_time (float,np.ndarray) : Equal to the number of semichords travelled. See function calculate_reduced_time
    """
    wagner = (1 - 0.165 * np.exp(-0.0455 * reduced_time) - 
                0.335 * np.exp(-0.3 * reduced_time))
    try:
        wagner[reduced_time < 0] = 0
    except:
        if reduced_time < 0:
            wagner = 0
    
    return wagner


def kussners_function(reduced_time: Union[np.ndarray,float]):
    """ 
    A commonly used approximation to Kussner's function (Sears and Sparks 1941)
    
    Args:
        reduced_time (float,np.ndarray) : This is equal to the number of semichords travelled. See function calculate_reduced_time
    """
    kussner = 1 - 0.5 * np.exp(-0.13 * reduced_time) - 0.5 * np.exp(-reduced_time) 
    
    try:
        kussner[reduced_time < 0 ] = 0 
    except:
        if reduced_time < 0:
            kussner = 0

    return kussner 



def calculate_wagner_lift_coefficient(
        reduced_time: Union[float,np.ndarray] , 
        angle_of_attack: float # In degrees
):
    """
    Computes the evolution of the lift coefficient in Wagner's problem which can be interpreted as follows
    1) An impulsively started flat plate at consntant angle of attack
    2) An impuslive change in the angle of attack of a flat plate at constant velocity
   
    The model predicts infinite added mass at the first instant due to the infinite acceleration
    The delta function term (and therefore added mass) has been ommited in this case.
    Reduced_time = 0 corresponds to the instance the airfoil pitches/accelerates
    
        Args:
        reduced_time (float,np.ndarray) : Reduced time, equal to the number of semichords travelled. See function reduced_time
        angle_of_attack (float) : The angle of attack in DEGREES

    """
    return 2 * np.pi * np.deg2rad(angle_of_attack) * wagners_function(reduced_time)


def calculate_kussner_lift_coefficient(
        reduced_time: Union[float,np.ndarray] , 
        gust_strength:float ,
        velocity: float,
        angle_of_attack : float = 0, # In degrees
        chord: float = 1
):
    """
    Computes the evolution of the lift coefficient of a flat plate entering a 
    sharp, transverse, top hat gust at a constant angle of attack
    Reduced_time = 0 corresponds to the instance the gust is entered
    
    
    (Leishman, Principles of Helicopter Aerodynamics, S8.10,S8.11)
    
    Args:
        reduced_time (float,np.ndarray) : Reduced time, equal to the number of semichords travelled. See function reduced_time
        gust_strength (float) : velocity in m/s of the top hat gust
        velocity (float) : velocity of the thin airfoil entering the gust
        angle_of_attack (float) : The angle of attack, in degrees
    """
    angle_of_attack_radians = np.deg2rad(angle_of_attack)
    offset = chord / 2 * (1 - np.cos(angle_of_attack_radians))
    return (2 * np.pi * 
            np.arctan(gust_strength / velocity) * 
            np.cos(angle_of_attack_radians) *
            kussners_function(reduced_time - offset))






def calculate_reduced_time(
        time: Union[float,np.ndarray],
        velocity: Union[float,np.ndarray],
        chord: float 
) -> Union[float,np.ndarray]:
    """ 
    Calculates reduced time from time in seconds and velocity history in m/s. For constant velocity it reduces to s = 2*U*t/c
    The reduced time is the number of semichords travelled by the airfoil/aircaft i.e. 2 / chord * integral from t0 to t of velocity dt  
    
    
    Args:
        time (float,np.ndarray) : Time in seconds 
        velocity (float,np.ndarray) : Either constant velocity or array of velocities at corresponding times
        chord (float) : The chord of the airfoil
        
    Returns:
        The reduced time as an array or similar to the input. The first element is 0. 
    """
    
    if type(velocity) == float or type(velocity) == int : 
        return 2 * velocity * time / chord
    else:
        assert np.size(velocity) == np.size(time) , "The velocity history and time must have the same length"
        reduced_time = np.zeros_like(time)
        for i in range(len(time)-1):
            reduced_time[i+1] =  reduced_time[i] + (velocity[i+1] + velocity[i])/2 * (time[i+1]-time[i])        
        return 2 / chord * reduced_time
    
    
def duhamel_integral_kussner(
        reduced_time: np.ndarray,
        gust_velocity: np.ndarray,
        velocity: float
): 
    """
    Calculates the duhamel superposition integral of Kussner's problem. 
    Given some arbitrary transverse velocity profile, the lift coefficient 
    as a function of reduced time of a flat plate can be computed using this function
    
    
    Args:
        reduced_time (float,np.ndarray) : Reduced time, equal to the number of semichords travelled. See function reduced_time
        gust_velocity (np.ndarray) : The transverse velocity profile that the flate plate experiences
        velocity (float) :The velocity by which the flat plate enters the gust
        
    Returns:
        lift_coefficient (np.ndarray) : The lift coefficient history of the flat plate 
    """
    assert np.size(reduced_time) == np.size(gust_velocity),  "The velocity history and time must have the same length"
    
    dw_ds = np.gradient(gust_velocity,reduced_time)
    lift_coefficient = np.zeros_like(reduced_time)
    kussner = kussners_function(reduced_time)
    ds =  np.gradient(reduced_time)
    
    for i in range(len(reduced_time)):
        integral_term = 0
        for j in range(i):
            integral_term += dw_ds[j]  * kussner[i-j] * ds[j]
        lift_coefficient[i] = 2 * np.pi / velocity * (gust_velocity[0] * kussner[i] + integral_term)
    
    return lift_coefficient

def modified_duhamel_integral_kussner(
        reduced_time: np.ndarray,
        gust_velocity: np.ndarray,
        velocity: float,
        angle_of_attack: float = 0, # In Degrees
        chord: float = 1 
): 
    """
    Calculates the duhamel superposition integral of Kussner's problem. 
    Given some arbitrary transverse velocity profile, the lift coefficient 
    as a function of reduced time of a flat plate can be computed using this function
    
    
    Args:
        reduced_time (float,np.ndarray) : Reduced time, equal to the number of semichords travelled. See function reduced_time
        gust_velocity (np.ndarray) : The transverse velocity profile that the flate plate experiences
        velocity (float) :The velocity by which the flat plate enters the gust
        
    Returns:
        lift_coefficient (np.ndarray) : The lift coefficient history of the flat plate 
    """
    assert np.size(reduced_time) == np.size(gust_velocity),  "The velocity history and time must have the same length"
    
    offset = chord / 2 * (1 - np.cos(np.deg2rad(angle_of_attack)))
    kussner = kussners_function(reduced_time)
    dK_ds = np.gradient(kussner,reduced_time)
    lift_coefficient = np.zeros_like(reduced_time)
    
    ds =  np.gradient(reduced_time)
    
    for i in range(len(reduced_time)):
        integral_term = 0
        for j in range(i):
            integral_term += dK_ds[j]  * gust_velocity[i-j] * ds[j]
        lift_coefficient[i] = 2 * np.pi / velocity * (gust_velocity[i] * kussner[0] + integral_term)
    
    return lift_coefficient



def duhamel_integral_wagner(
        reduced_time: np.ndarray,
        angle_of_attack: np.ndarray # In degrees
): 
    """
    Calculates the duhamel superposition integral of Wagner's problem. 
    Given some arbitrary pitching profile, the lift coefficient as a function 
    of reduced time of a flat plate can be computed using this function
    
    
    Args:
        reduced_time (float,np.ndarray) : Reduced time, equal to the number of semichords travelled. See function reduced_time
        angle_of_attack (np.ndarray) : The angle of attack as a function of reduced time of the flat plate
    Returns:
        lift_coefficient (np.ndarray) : The lift coefficient history of the flat plate 
    """
    assert np.size(reduced_time) == np.size(angle_of_attack),  "The pitching history and time must have the same length"
    
    angle_of_attack = np.deg2rad(angle_of_attack)
    da_ds = np.gradient(angle_of_attack,reduced_time)
    lift_coefficient = np.zeros_like(reduced_time)
    wagner = wagners_function(reduced_time)
    ds =  np.gradient(reduced_time)
    
    for i,s in enumerate(reduced_time):
        lift_coefficient[i] = 2 * np.pi * (angle_of_attack[0] * wagner[i] + np.sum([da_ds[j]  * wagner[i-j] * ds[j] for j in range(i)]))
    
    return lift_coefficient




def non_circulatory_lift_from_pitching(
        reduced_time: np.ndarray,
        angle_of_attack: np.ndarray # In degrees
):
    
    """
    This function calculate the lift coefficient due to the added mass of a wing
    pitching about its midchord moving at constant velocity. 
    
    Args:
        reduced_time (np.ndarray) : Reduced time, equal to the number of semichords travelled. See function reduced_time
        angle_of_attack (np.ndarray) : The angle of attack as a function of reduced time of the flat plate
    Returns:
        lift_coefficient (np.ndarray) : The lift coefficient history of the flat plate 
    """

    angle_of_attack = np.deg2rad(angle_of_attack)
    da_ds = np.gradient(angle_of_attack,reduced_time)
    # TODO: generalize to all unsteady motion
    
    return np.pi / 2 * np.cos(angle_of_attack)**2 * da_ds
    
    

def pitching_through_transverse_gust():
    """
    This function calculates the lift coefficient history of a wing 
    """
    pass


if __name__ == "__main__":
    
    
    
    n = 1000
    n1 = int(n/3)
    n2 = int(2*n/3)
    time = np.linspace(0,100,n)
    velocity = 0.2
    chord = 1
    reduced_time = calculate_reduced_time(time, velocity, chord) 
    
     
    angle_of_attack = 20*np.deg2rad(np.sin(reduced_time))
    angle_of_attack[n1:n2] = np.deg2rad(-20)
    
    
    gust_velocity = np.zeros_like(reduced_time)
    gust_velocity[n1:n2] = velocity 
    
    angle_of_attack = 20*np.deg2rad(np.sin(reduced_time))
    angle_of_attack[n1:n2] = np.deg2rad(-20)
    
    cl_k = duhamel_integral_kussner(reduced_time,gust_velocity,velocity)
    cl_k2 = modified_duhamel_integral_kussner(reduced_time,gust_velocity,velocity)

    cl_w = duhamel_integral_wagner(reduced_time,angle_of_attack)
        
    plt.figure(dpi=300)
    plt.plot(reduced_time,cl_k,label="kussner")
    plt.plot(reduced_time,cl_k2,label="kussner",ls="--")
    plt.xlabel("Reduced time, t*")
    plt.ylabel("$C_\ell$")
    plt.legend()



