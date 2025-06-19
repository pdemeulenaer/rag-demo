**Abstract**

The full text of the scientific paper has been segmented into logical sections as requested. The resulting sections are:

**ABSTRACT**

A&A 550, A20 (2013)
DOI: 10.1051/0004-6361/201220674
c⃝ESO 2013
Astronomy
&
Astrophysics
Deriving physical parameters of unresolved star clusters
I. Age, mass, and extinction degeneracies⋆
P. de Meulenaer1,2, D. Narbutis1, T. Mineikis1,2, and V. Vanseviˇcius1,2
1 Vilnius University Observatory, ˇCiurlionio 29, 03100 Vilnius, Lithuania
e-mail: philippe.demeulenaer@ff.stud.vu.lt
2 Center for Physical Sciences and Technology, Savanoriu¸ 231, 02300 Vilnius, Lithuania
Received 31 October 2012 / Accepted 28 November 2012
ABSTRACT
Context. Stochasticity and physical parameter degeneracy problems complicate the derivation of the parameters (age, mass, and ex-
tinction) of unresolved star clusters when using broad-band photometry.
Aims. We develop a method to simulate stochasticity and degeneracies and to investigate their inﬂuence on the accuracy of derived
physical parameters. Then we apply it to star cluster samples of M 31 and M 33 galaxies.
Methods. Age, mass, and extinction of observed star clusters are derived by comparing their broad-band UBVRI integrated magni-
tudes to the magnitudes of a large grid of star cluster models with ﬁxed metallicity Z = 0.008. Masses of stars for a cluster model
are randomly sampled from the initial mass function. Models of star clusters from the model grid, which have all of their magnitudes
located within 3 observational errors from the magnitudes of the observed cluster, are selected for computing their age, mass, and
extinction.
Results. In the case of the M 31 galaxy, the extinction range is wide and the age-extinction degeneracy is strong for a fraction of its
clusters. Because of a narrower extinction range, the age-extinction degeneracy is weaker for the M 33 clusters. By using artiﬁcial
cluster sample, we show that age-extinction degeneracy can be reduced signiﬁcantly if the range of intrinsic extinction within the host
galaxy is narrow.
Key words. galaxies: star clusters: general

**1. Introduction**

1. Introduction
Star clusters are important objects for understanding the forma-
tion and evolution of their host galaxies. It is considered that
most of star formation is clustered (Lada & Lada 2003), there-
fore knowledge of the physical parameters of a cluster popu-
lation (e.g., age, mass, chemical composition, and extinction) is
essential for constraining the star formation history of the galaxy.
The commonly used method for deriving the physical param-
eters of unresolved star clusters is based on comparing of their
integrated broad-band photometry colors to the colors of simple
stellar population (SSP) models; see, e.g., Anders et al. (2004)
and Bridžius et al. (2008). However, this method is strongly bi-
ased by the presence of two major problems:
– degeneracy between various physical parameters of star clus-
ters; see, e.g., Worthey (1994), Bridžius et al. (2008). For ex-
ample, a young cluster possessing high extinction can have
colors similar to an older object without extinction – an age-
extinction degeneracy;
– stochasticity, which is due to the random presence of a
few bright stars, which dominate the integrated photome-
try of unresolved clusters; see, e.g., Santos & Frogel (1997),
Deveikis et al. (2008), Maíz Apellániz (2009). Young clus-
ters can have supergiant stars that signiﬁcantly redden their
integrated colors. By using the SSP method, a much older
age would be determined for these clusters.
⋆Figures 6–8 are available in electronic form at
http://www.aanda.org
Although Cerviño & Luridiana (2006) have attempted to de-
scribe the problem of stochasticity analytically, the currently
preferred approach (e.g., Popescu & Hanson 2009, 2010;
Fouesneau & Lançon 2010; Fouesneau et al. 2012; Asa’D &
Hanson 2012) is to use a Monte-Carlo sampling of stellar initial
mass function (IMF) to model integrated colors of clusters and
build an extensive grid of models, to cover all possible age, mass
and extinction ranges. Physical parameters of star clusters are
then derived by comparing observations to the grid of models.
Recently Asa’D & Hanson (2012) have derived the age
and extinction of star clusters in the Large Magellanic Cloud
(LMC) using the method of Popescu & Hanson (2010) that
takes stochasticity into account, and compared results to previ-
ous derivations based on an isochrone ﬁt to the resolved color-
magnitude diagrams (CMDs). They managed to constrain the
age of clusters similar to the values found by the isochrone ﬁt
only when previously known extinctions of individual clusters
were used.
In this paper, a method of deriving physical parameters is
developed and applied to star cluster samples (integrated multi-
band photometry) in two Local Group galaxies: 1) M 31, using a
catalog by Vanseviˇcius et al. (2009), who derived cluster param-
eters using SSP method; and 2) M 33, using objects common
to catalogs of Ma (2012) for photometry and San Roman et al.
(2009), who observed in resolved conditions with the Hubble
Space Telescope (HST) and estimated age, mass, and extinction
based on an isochrone ﬁt to cluster CMDs.
Using this data and artiﬁcial cluster simulations, we demon-
strate that when the intrinsic range of extinction within the host
Article published by EDP Sciences
A20, page 1 of 10
A&A 550, A20 (2013)

**2. Method of deriving age, mass, and extinction of star cluster**

2. Method of deriving age, mass, and extinction
of star cluster
There are presently two main methods used to derive physical
parameters of star clusters based on a 3D grid (age, mass and
extinction) of models, which take stochasticity eﬀects into ac-
count. The ﬁrst is a fast χ2 minimization approach used by, e.g.,
Popescu & Hanson (2010) and Beerman et al. (2012), the sec-
ond, a more accurate but much slower approach, which builds
probability maps in the age-mass-extinction space by exploring
all the nodes of the grid and selects the most probable solution
(see e.g., Fouesneau & Lançon 2010).
The method presented here also explores parameter proba-
bility maps; however, by restricting the analysis to the models
located in the vicinity of the observed absolute magnitudes (the
distance to the object has to be known), we signiﬁcantly reduce
the computation time. The scheme of the method is sketched in
Fig. 1.
A 3D grid of cluster models is built for every value of the
three physical parameters t, m, E(B −V)1; for simplicity Fig. 1a
shows only a grid for age and mass. For the description of the
grid, see Sect. 3. Each node of the grid contains 1000 models
of the same age, mass, and extinction. They populate the photo-
metric parameter space (absolute UBVRI magnitudes). Figure 1b
shows MU and MB with only 100 models per node without ex-
tinction, and the used model grid is much more continuous in
photometric parameter space.
When the observations are considered in Fig. 1c, along with
their error bars (σ; hereafter we use σ = 0.05 mag for all the
passbands of artiﬁcial and real cluster samples studied in this
paper), which in general can be diﬀerent for every magnitude, all
the models situated within 3–σ from the observed magnitudes
are selected. Figure 1d shows the nodes to which the selected
models are associated. Other nodes do not play any role in the
derivation of parameters, therefore the speed of the algorithm is
increased signiﬁcantly. Finally, the distributions of age and mass,
displayed in Figs. 1e, f, are derived from the selected models, as
for the extinction, which is not shown in the ﬁgure.

**3. The age-mass-extinction grid of models**

3. The age-mass-extinction grid of models
To derive physical parameters of star clusters with the method
described in Sect. 2, a large age-mass-extinction grid of models
is computed, by applying the algorithm described by Deveikis
et al. (2008). The stellar masses are generated randomly sam-
pling the IMF (corrected for binaries; Kroupa 2001) and their
luminosities are derived from stellar isochrone of the selected
age and metallicity of the cluster model. The process is contin-
ued until the total mass of generated stars reaches the mass of the
cluster model. Then, taking the distance to the cluster into ac-
count, the magnitudes are computed using the Johnson-Cousins
UBVRI photometric system (Maíz Apellániz 2006).
For stellar models, we took the PADOVA isochrones2
from Marigo et al. (2008), with corrections by Girardi et al.
(2010) for the TP-AGB phases. The model grid for a single
2 PADOVA isochrones from “CMD 2.4”: http://stev.oapd.inaf.
it/cmd
A20, page 2 of 10
P. de Meulenaer et al.: Deriving physical parameters of unresolved star clusters. I.
metallicity Z = 0.008 contains the following nodes: ages from
log (t/yr)
=
6.6 to 10.1 in steps of 0.05, masses from
log (m/M⊙) = 2 to 5 in steps of 0.05. This gives 71 values of
age and 61 values of mass, and the grid consists of 1000 models
per node, i.e. ∼4×106 stochastic models. To limit the number of
models to store in computer’s memory, extinction is computed
when the observed cluster is compared with the grid of models.
It ranges from E(B −V) = 0 to 1 in steps of 0.02, therefore
51 values for the extinction.
To accelerate computation of integrated magnitudes of
stochastic star cluster models, we deﬁned a threshold in the
isochrone, under which the total luminosity of fainter stars is
computed by integration of the stellar luminosity function along
the isochrone. Above the threshold, which is deﬁned to se-
lect 20% of the most massive stars, the contribution of the high-
mass stars is modeled by the algorithm of Deveikis et al. (2008).
The models built by this improved procedure share the same
properties as models built by simulating all stars of the clus-
ter, but require much less computation with a speed gain of a
factor ∼10.

**4. Test of the method on an artiﬁcial cluster sample**

4. Test of the method on an artiﬁcial cluster sample
4.1. Degeneracies in an artiﬁcial cluster sample
We simulated artiﬁcial star cluster samples with known age,
mass, and extinction and used them as input clusters to evalu-
ate the ability of our method to derive physical parameters. The
artiﬁcial cluster samples consist of 10 000 clusters with a random
age in the log (t/yr) range of [6.6, 10.1]. To simulate the mass of
input clusters, we used a power-law cluster mass function with
index −2 in the range of log (m/M⊙) = [2.7, 4.3], so as to have
more low-mass clusters in the sample. We have two artiﬁcial
samples: one without extinction and the other with E(B −V) in
the range of [0.0, 1.0] using the Milky Way standard extinction
law from Cardelli et al. (1989).

**5. Application of the method to real star clusters**

5. Application of the method to real star clusters
5.1. The M 31 galaxy star cluster sample
A star cluster catalog of 285 objects located in the south west
ﬁeld of the M 31 galaxy was compiled by Narbutis et al. (2008)
using the deep BVRI and Hα photometry from the Subaru tele-
scope, as well as multiband maps based on HST, Galex, Spitzer,
and 2MASS imaging. The UBVRI photometry was derived us-
ing the Local Group Galaxy Survey data from Massey et al.
(2006). The magnitude limit of the cluster sample was set to
the V = 20.5 mag.
Vanseviˇcius et al. (2009) selected 238 clusters from that sam-
ple, excluding the ones with strong Hα emission, and compared
their multiband colors to PEGASE (Fioc & Rocca-Volmerange
1997) SSP models to derive their age, mass, metallicity, and ex-
tinction. Spitzer data was used to constrain the maximum ex-
tinction for each cluster. They reported ∼30 classical globular
A20, page 5 of 10
A&A 550, A20 (2013)
clusters with low metallicity older than 3 Gyr. The remain-
ing ∼210 younger clusters were classiﬁed as objects belonging
to the disk, with average metallicity Z = 0.008. Figure 5 shows
the U −B vs. B −V and U −V vs. R −I diagrams of the 238 star
clusters from Vanseviˇcius et al. (2009), compared to the grid of
star cluster models built in Sect. 3.
Since our grid of models has single metallicity, Z
=
0.008, we attempted to exclude more metal-rich clusters from
Vanseviˇcius et al. (2009) sample by only selecting objects with
galactocentric distance over 7 kpc. This subsample consists of
216 clusters and is displayed in Fig. 5. It is studied with our
method described in Sect. 2, using the Milky Way standard ex-
tinction law (Cardelli et al. 1989) and distance modulus to M 31
of (m −M)0 = 24.47 derived by McConnachie et al. (2005).
Figure 6 presents the age (panels a, b, c), mass (panels d,
e, f) and extinction (g, h, i) of 211 clusters (from the 216 sam-
ple) derived by using our method; for ﬁve clusters, no model
was found within the 3–σ around the observed magnitudes.
Clusters were studied twice, ﬁrst with a narrow extinction range
E(B −V) = [0.04, 0.5] allowed in the model grid, and second
with a wider one, [0.04, 1.0].