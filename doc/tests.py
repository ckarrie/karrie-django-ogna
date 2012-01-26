from karrie.django.ogna import models

proj1 = models.Project.objects.get(name="Mainz")
proj2 = models.Project.objects.get(name="Basel")

from karrie.django.ogna.models import Project
mz = Project.objects.get(name="Mainz")
a_dist = Project.objects.distance(mz.center)
a_dist[0].distance
a_azimuth = Project.objects.azimuth(mz.center)
a_azimuth[0].azimuth