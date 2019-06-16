from Classes import *
import ExampleAirplanes

a = ExampleAirplanes.conventional()
#a.set_paneling_everywhere(2,2)
ap = AeroProblem(
    airplane=a,
    op_point=OperatingPoint(velocity=10,
                            alpha=5,
                            beta=0),
)
ap.make_vlm1_problem()

# a.draw()
ap.draw_panels()