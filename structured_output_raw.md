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
galaxy is rather narrow, it is not necessary to know the exact
value of the extinction for individual clusters to derive their
physical parameters reliably.
The paper is organized into the following sections. Section 2
introduces our method of deriving physical parameters of clus-
ters when stochasticity is taken into account, Sect. 3 describes a
grid of simulated cluster models, Sect. 4 presents tests of the
method on artiﬁcial cluster samples, and Sect. 5 applies the
method to the M 31 and M 33 star clusters.
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
For the selected models (Fig. 1c circle) we apply weights
as follows: for the models located within 1–σ from the ob-
served magnitude a weight of 0.68 is assigned, for the ones
between 1–σ and 2–σ – 0.28, and for the ones between 2–σ
and 3–σ – 0.04. The probability density distributions displayed
in Figs. 1e, f are derived by normalizing the total area of each
histogram to 1. The solution is taken as the maximum of these
1D distributions. We compute conﬁdence intervals (error bars)
by excluding the ﬁrst and the last 16% of the area in his-
tograms, following the method of “central interval” presented
in Sect. 2.5.1 of Andrae (2010).
1 We refer to extinction as E(B −V) hereafter.
physical
photometric
Space of parameters
a)
d)
b)
c)

log(
/ M )
m
log( / yr)
t

log(
/ M )
m
log( / yr)
t

log(
/ M )
m
2
4
6
0
0.1
0.2
log( / yr)
t
Probability density
7
8
9
10
0
0.04
0.08
0.12
−4.6
−4.4
−4.2
−4.0
−4.6
−4.4
−4.2
−4.0
Probability density
e)
f)
U
M
B
M
U
M
B
M
U
σ
B
σ
Fig. 1. Scheme of the method for deriving physical parameters of star
cluster. Panel a) shows the grid of models (only age and mass are dis-
played; same for extinction). These models are represented in the pho-
tometric space (only MU and MB are shown) displayed in panel b);
only 100 models per node without extinction are shown). In panel c)
all the models situated within 3–σ (circle) from the observed absolute
magnitudes are selected. Panel d) shows the nodes associated with these
models. The 1D age and mass distributions of the selected models are
displayed as normalized histograms in panels e) and f), used to deter-
mine most probable values, indicated by solid vertical lines; conﬁdence
intervals are indicated by dashed lines.
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
Figure 2 displays the results for artiﬁcial cluster sample built
without extinction. Panels (a) and (b) show results of the age and
mass of the artiﬁcial cluster sample without introducing pho-
tometric observation errors. Panels (c) and (d) show the case
with Gaussian photometric errors of 0.05 mag randomly added
to each magnitude of the sample clusters. The introduction of
photometric errors results in broadening around the one-to-one
line.
In Fig. 2b, the asymmetry observed in the mass derivation
slightly favors high masses. This is because that in the grid
of star cluster models, the nodes of models with higher mass
have magnitudes that are less dispersed than the nodes with
lower mass models, as a consequence of stochasticity (see e.g.,
Deveikis et al. 2008). Thus, when the models of two nodes
of diﬀerent masses are located in the UBVRI “sphere” around
the observation shown in Fig. 1c, the more massive node, with
less dispersed models, will dominate. To balance out the eﬀect,
a cluster mass function could be used to decrease the impor-
tance of the nodes of massive cluster models. Although Fig. 2b
shows asymmetry, the means and standard deviations given at
log (m/M⊙) = 3.0, 3.5, and 4.0 indicate that this phenomenon is
slight.
Figure 3 gives the results of artiﬁcial clusters in the case
of extinction. Panels (a), (b), and (c) show the age, mass and
extinction derived when there is no photometric errors, and pan-
els (d), (e), and (f) when there are Gaussian photometric er-
rors of 0.05 mag included. In Fig. 3d, in the case of photomet-
ric errors and extinction, we observe that a broadening around
the one-to-one relation increases, especially for log (t/yr) ≳8,
10
9
8
7
10
9
8
7
log( / yr) derived
t
10
9
8
7
log( / yr) true
t
5
4
3
5
4
3

log(
/ M ) derived
m
5
4
3

log(
/ M ) true
m
a)
c)
b)
d)
Number of models per bin
3
10
30
100
Fig. 2. Derived parameters of 10 000 artiﬁcial clusters without extinc-
tion. Panels a) and b) show age and mass for a sample without photo-
metric errors; c) and d) for a sample with Gaussian photometric errors
of 0.05 mag. Panel b) also shows the means and standard deviations
(circles with error bars) of the derived mass distributions for clusters
with true mass log (m/M⊙) = 3.0, 3.5 and 4.0. The density scale is
logarithmic.
which is associated with broadening in the extinction (panel f),
which is a sign of the age-extinction degeneracy. It creates two
streaks above and below the one-to-one relation in the range
of 8 <∼log (t/yr) <∼9.5 that were already perceptible in the
case without photometric errors in Fig. 3a. However, including
of photometric errors does not signiﬁcantly aﬀect the derivation
of mass (panels b and e). We note that a gap in derived ages at
log (t/yr) = 9.15 is a feature of isochrone due to the increase in
the production rate of AGB stars, which was discussed in Girardi
& Bertelli (1998).
These degeneracy streaks have ﬁrst been reported by
Fouesneau & Lançon (2010). The degeneracy streak above the
one-to-one line seen in Fig. 3d concerns clusters that are young
and that possess intrinsically high extinction, but are derived by
the method as older and having lower extinction. Conversely, the
streak of clusters below the one-to-one relation involves objects
that are derived as older and that have lower extinction than they
do in reality. These features are important to keep in mind when
deriving the physical parameters of unresolved star clusters.
The treatment of the metallicity eﬀects on the derivation of
age, mass, and extinction of star clusters is the subject of a forth-
coming paper. To illustrate the eﬀect, we derived the parameters
of a cluster sample of Z = 0.008 metallicity, successively with a
model grid of much lower metallicity, Z = 0.00013, and another
one with much higher metallicity, Z = 0.03. In the ﬁrst case,
the ages are systematically overestimated by ∼0.5 dex, the up-
per streak is more developed, and the lower one disappears. The
masses are also overestimated by ∼0.5 dex, and there is a pref-
erence for overestimated extinction. In the second case, the ages
are only slightly (∼0.1 dex) underestimated. The upper streak
decreases without vanishing, and the lower one becomes more
populated. The masses are underestimated of ∼0.1 dex, and the
extinction is almost unaﬀected.
A20, page 3 of 10
A&A 550, A20 (2013)
a)
10
9
8
7
10
9
8
7
10
9
8
7
d)
log( / yr) true
t
log( / yr) derived
t
b)
e)
5
4
3
5
4
3
5
4
3

log(
/ M ) true
m

log(
/ M ) derived
m
c)
f)
−
(
) true
E B
V
−
(
) derived
E B
V
0
0.4
0.8
0.4
0.8
0
0.4
0.8
0
100
30
10
3
Number of models per bin
Fig. 3. Derived parameters of 10 000 artiﬁcial clusters with extinction randomly chosen in the range of E(B−V) = [0, 1]. Panels a), b) and c) show
age, mass, and extinction for a sample without photometric errors; d), e), and f) for a sample with Gaussian photometric errors of 0.05 mag.
4.2. Is it possible to reduce the age-extinction degeneracy?
The upper and lower streaks in Fig. 3d suggest that if a wide ex-
tinction range is allowed in a simulated sample, then there are
possibilities that a cluster mimics an older one with lower ex-
tinction, or inversely a younger one with higher extinction. If
the true extinction range of the cluster population is narrow, then
we could restrict the search for the extinction within a narrow
range in the model grid, resulting in decrease of age-extinction
degeneracy.
In Fig. 4 we show results of the tests for a sample of 10 000
artiﬁcial clusters with true extinction from a range of E(B−V) =
[0, 0.5] and with Gaussian photometric errors of 0.05 mag ran-
domly added to each magnitude of the sample clusters. This
cluster sample was studied twice, with diﬀerent allowed extinc-
tion ranges in the model grid.
In the ﬁrst test, the extinction of the model grid was allowed
to vary in a wide range, E(B −V) = [0, 1], shown in Figs. 4a−c.
If a cluster has a true extinction of 0.5, then the maximum under-
estimation of its extinction can be from 0 to 0.5. But if a cluster
has true extinction of 0, the maximum overestimation of its ex-
tinction could range from 0 to 1. This explains why the lower
streak (i.e. clusters with overestimated extinction) is more ex-
tended than the upper one in panel (a).
In the second test, the allowed extinction range of the model
grid was reduced to a range of [0, 0.5]; Figs. 4d–f. The constraint
on the extinction range resulted in a reduction of the lower de-
generacy streak, seen in Fig. 4d, which is less developed than in
Fig. 4a. From the comparison of Figs. 4b and e, we see that the
mass is less aﬀected by the degeneracy. We note that only the
lower streak is modiﬁed, since only the higher limit of the al-
lowed extinction range was changed from 1.0 to 0.5. The upper
streak is not modiﬁed, because the lower limit of the allowed
extinction range was not changed.
To quantify the reduction of the lower degeneracy streak
due to reduction of the extinction range, all the models situ-
ated in the square shown in Figs. 4a and d were counted. There
are ∼480 clusters in that region for the wide extinction range
(panel a) and only ∼110 for the low extinction range (panel d).
The reduction of the extinction range from E(B −V) = [0, 1]
to [0, 0.5] thus decreases more than four times the strength of
the degeneracy streak.
We conclude that to reduce the degeneracy streaks seen in
Fig. 3d, we should make a reasonable assumption on the extent
of the possible extinction range within the galaxy hosting the
studied cluster population.
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
A20, page 4 of 10
P. de Meulenaer et al.: Deriving physical parameters of unresolved star clusters. I.
a)
d)
b)
e)
c)
f)
10
9
8
7
log( / yr) true
t
5
4
3

log(
/ M ) true
m
−
(
) true
E B
V
0
0.2
0.4
−
(
) derived
E B
V
0.4
0.8
0
0.4
0.8
0
5
4
3
5
4
3

log(
/ M ) derived
m
10
9
8
7
10
9
8
7
log( / yr) derived
t
100
30
10
3
Number of models per bin
Fig. 4. Derived parameters of 10 000 artiﬁcial clusters with true extinction randomly chosen in the range of E(B −V) = [0, 0.5] with Gaussian
photometric errors of 0.05 mag. Panels a), b), and c) show age, mass and extinction when a sample is studied using a grid of models with an
allowed extinction in the range of [0, 1]; d), e), and f) show results for the same cluster sample studied with a narrower allowed extinction in the
range of [0, 0.5]. Panels c) and f) are denser than in Fig. 3, because the same number of clusters are located on a smaller range of extinction. A
square indicated in panels a) and d) is used to quantify the degeneracy eﬀect.
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
with a wider one, [0.04, 1.0]. The ﬁrst column (panels a, d,
g) compares the age, mass, and extinction derived when a nar-
row extinction range is allowed vs. the Vanseviˇcius et al. (2009)
results. The second column (panels b, e, h) compares the age,
mass, and extinction derived when a wide extinction range is al-
lowed vs. the Vanseviˇcius et al. (2009) results. The last column
(panels c, f, i) compares the results obtained with a wide extinc-
tion range allowed vs. the ones obtained with a narrow extinction
range allowed.
In Fig. 6a, when clusters are studied in a narrow allowed ex-
tinction range, E(B−V) = [0.04, 0.5], the derived ages show the
same features as the models studied in Fig. 3d, reproduced here
in the background of the panel. The degeneracy streaks develop
above and below the one-to-one line, perpendicularly to it, and
are marked by ellipses numbered “1” and “2” in Fig. 6a. As for
the models in the background, the upper degeneracy streak con-
cerns clusters with overestimated age and underestimated extinc-
tion, shown by ellipse “1” in Fig. 6g. In contrast, for the lower
degeneracy streak (ellipse “2”), the age is underestimated and
extinction is overestimated. Since the upper streak (ellipse “1”)
is more developed than the lower one (“2”), we interpret that
as a result of too narrow an extinction range in the model grid
allowed E(B −V) = [0.04, 0.5].
In Fig. 6b, when clusters are studied in a wider model extinc-
tion range, E(B −V) = [0.04, 1], the upper degeneracy streak is
less populated, and the lower one extends, meaning that some
of the clusters have overestimated extinction (ellipse “3”), also
shown in panel (h).
If the intrinsic range of extinction for a cluster sample is
wide, as in the galaxy M 31, then a narrow extinction range of
models produces extended an upper streak (ellipse “1”) and a
smaller lower streak (ellipse “2”), shown in Fig. 6a. In panel (b),
when the allowed extinction range of models is wide, the upper
streak retracts and the lower streak develops. We conclude that in
a galaxy with wide extinction range, it is not possible to derive
parameters for the clusters aﬀected by age-extinction degener-
acy and additional constraints for the extinction are needed; e.g.,
Vanseviˇcius et al. (2009) used a Spitzer emission map, to trace
the dust lanes of M 31 and reduce the age-extinction degeneracy.
Figures 6d, e show that for high-mass clusters we obtain
lower masses than given by Vanseviˇcius et al. (2009). Inspecting
the metallicity values provided by Vanseviˇcius et al. (2009),
A20, page 5 of 10
A&A 550, A20 (2013)
−1.0
−0.5
0
0.5
1.0
1.5
−0.5
0
0.5
1.0
1.5
−1
0
1
2
3
−0.5
0
0.5
1.0
1.5
2.0
a)
b)
−
B
V
−
R
I
−
U
B
−
U
V
Fig. 5. M 31 galaxy star cluster sample of 238 objects from Vanseviˇcius et al. (2009) (circles and stars) and the studied sample of 216 objects
(stars) having galactocentric distance over 7 kpc. Panels show: a) U −B vs. B −V and b) U −V vs. R −I diagrams. The model grid (without
extinction) used to derive physical parameters of clusters is displayed in the background with indicated reddening vectors following the Galactic
extinction law. The continuous line traces PADOVA SSP of Z = 0.008.
we note that high-mass clusters have metallicities lower than
the Z = 0.008 used in our model grid. This could be a sign of the
metallicity eﬀect on the derivation of physical parameters, and
will be investigated in the forthcoming paper.
5.2. The M 33 galaxy star cluster sample
San Roman et al. (2009) reports observing of 161 clusters using
the HST, allowing them to evaluate their ages and extinctions
by PADOVA Girardi et al. (2002) isochrone ﬁt to their resolved
CMDs. Recently, Ma (2012) has used 392 clusters from the com-
piled catalog of Sarajedini & Mancone (2007) and images from
Massey et al. (2006) to provide UBVRI broad-band integrated
photometry data.
There are 40 clusters common to both the San Roman et al.
(2009) and the Ma (2012) catalogs, making them interesting
to compare the parameters derived from the resolved method
(isochrone ﬁt to CMDs by San Roman et al. 2009) and stochas-
tic method, which was applied here to the integrated photometry
data of Ma (2012).
Figure 7a presents the U −B vs. B −V diagram of the
392 clusters from the Ma (2012) catalog compared to the grid
of cluster models. The selected 40 star clusters are also indi-
cated. To account for calibration of the B band, as discussed
by Ma (2012), where he compared his photometry to previous
works by Sarajedini & Mancone (2007), Park & Lee (2007), and
San Roman et al. (2009), we shifted the B band to brighter mag-
nitudes by 0.1 mag for all clusters. We note that the parameter
derivation results do not change when the B band is not taken
into account.
Since the metallicity content of the M 33 galaxy is similar
to the one of the LMC (Bresolin et al. 2010), we assume that
the interstellar extinction law derived by Gordon et al. (2003)
for the LMC can be applied to the M 33 cluster sample. As in
San Roman et al. (2009), we adopted the M 33 distance modulus
of (m −M)0 = 24.54 (McConnachie et al. 2005).
For the M 33, U et al. (2009) derived the extinction of 22 su-
pergiants, which resulted in an extinction distribution centered
on E(B −V) = 0.1. U et al. (2009) also used the data of
Rosolowsky & Simon (2008) to derive E(B −V) values for
58 HII regions, and show in their Fig. 9 that extinction can be
expected to be E(B−V) <∼0.3 for those regions (except for 3 ob-
jects), with an average E(B −V) ∼0.11. A foreground Galactic
line-of-sight extinction in the direction of M 33 of E(B −V) =
0.04 is estimated from Schlegel et al. (1998) extinction maps.
We studied the M 33 clusters using two diﬀerent allowed ex-
tinction ranges for the model grid. The ﬁrst one is narrow, ex-
tending between the foreground Galactic line-of-sight extinction
in the direction of M 33 up to the higher limit given by U et al.
(2009), i.e., E(B −V) = [0.04, 0.30]. The second one is a wider
extinction range, E(B −V) = [0.04, 1.0], such as the one used
for the M 31 case.
Figure 8 presents the age (panels a, b, c), mass (panels d,
e, f), and extinction (g, h, i) of the 40 clusters derived by using
our method. The results obtained in the narrow extinction range
(panels a, d, g) and the wide extinction range (panels b, e, h) are
compared to the ones obtained by San Roman et al. (2009) using
isochrone ﬁt to CMDs. Panels (c, f, i) compare the results we
obtained with the wide extinction range allowed vs. the narrow
extinction range allowed. It shows that the diﬀerence is relatively
small between the two kinds of solution, showing that the age-
degeneracy is playing a minor role in this M 33 cluster sample.
The derived mass does not diﬀer signiﬁcantly, as seen in
Fig. 8f. Panels (g, h, i) reveal that only one fourth of the clus-
ters are aﬀected by an increase in extinction when the allowed
extinction range is widened. Only some of them have a much
higher derived extinction when the wide allowed extinction
range is used. These few clusters aﬀected by the age-extinction
A20, page 6 of 10
P. de Meulenaer et al.: Deriving physical parameters of unresolved star clusters. I.
degeneracy can be seen in panel (c), appearing younger when a
wide extinction range is allowed than when the range is narrow,
as already seen in M 31 cluster sample in Fig. 6c.
6. Conclusions
We presented a method that aims to derive the age, mass, and
extinction of unresolved star clusters by using broad-band pho-
tometry and taking the stochastic sampling of stellar masses in
clusters into account. We investigated the behavior of the method
on a sample of artiﬁcial star clusters, in order to trace the dif-
ferent degeneracies between parameters, for diﬀerent choices of
photometric errors and extinction.
These tests allowed us to quantify the age-extinction de-
generacy. We demonstrated that for the intrinsically narrow
extinction range of the star cluster sample, the age-extinction
degeneracy can be resolved even in cases where individual exact
extinction values are not known for each cluster.
The age-extinction degeneracy has been observed in the real
star cluster sample of Vanseviˇcius et al. (2009) for M 31 and to
a lesser extent in the one composed of clusters common to the
Ma (2012) and San Roman et al. (2009) catalogs for M 33. The
physical parameters derived by our method for diﬀerent extinc-
tion ranges in each case, have been compared to the values pro-
vided in these studies, showing the impact of the age-extinction
degeneracy, especially when the true extinction range of the clus-
ter population is wide.
The M 31 star cluster sample from Vanseviˇcius et al. (2009)
showed that a true extinction range in this galaxy is wide enough,
so that the age-extinction degeneracy is signiﬁcantly developed,
making the parameters diﬃcult to derive, especially for older
ages. In such cases, it is preferable to use external constraints on
the extinction of individual clusters.
The M 33 star cluster sample shows little sign of age-
extinction degeneracy, since there is only a small diﬀerence be-
tween solutions in narrow and wide extinction ranges. The range
of allowed extinction of E(B −V) = [0.04, 0.30] gives param-
eters consistent with the results of isochrone ﬁt to CMDs by
San Roman et al. (2009).
The follow-up paper will be dedicated to study of the metal-
licity eﬀects to derive physical parameters of star clusters and
to gain a complete understanding of degeneracies introduced by
stochastic eﬀects.
Acknowledgements. We are grateful to the anonymous referee for fruitful com-
ments, which helped to improve the paper. This research was funded by a grant
(No. MIP-102/2011) from the Research Council of Lithuania.
References
Anders, P., Bissantz, N., Fritze-v. Alvensleben, U., & de Grijs, R. 2004,
MNRAS, 347, 196
Andrae, R. 2010 [arXiv:1009.2755]
Asa’D, R. S., & Hanson, M. M. 2012, MNRAS, 419, 2116
Beerman, L. C., Johnson, L. C., Fouesneau, M., et al. 2012, ApJ, 760, 104
Bresolin, F., Stasi´nska, G., Vílchez, J. M., Simon, J. D., & Rosolowsky, E. 2010,
MNRAS, 404, 1679
Bridžius, A., Narbutis, D., Stonkut˙e, R., Deveikis, V., & Vanseviˇcius, V. 2008,
Baltic Astron., 17, 337
Cardelli, J. A., Clayton, G. C., & Mathis, J. S. 1989, ApJ, 345, 245
Cerviño, M., & Luridiana, V. 2006, A&A, 451, 475
Deveikis, V., Narbutis, D., Stonkut˙e, R., Bridžius, A., & Vanseviˇcius, V. 2008,
Baltic Astron., 17, 351
Fioc, M., & Rocca-Volmerange, B. 1997, A&A, 326, 950
Fouesneau, M., & Lançon, A. 2010, A&A, 521, A22
Fouesneau, M., Lançon, A., Chandar, R., & Whitmore, B. C. 2012, ApJ, 750, 60
Girardi, L., & Bertelli, G. 1998, MNRAS, 300, 533
Girardi, L., Bertelli, G., Bressan, A., et al. 2002, A&A, 391, 195
Girardi, L., Williams, B. F., Gilbert, K. M., et al. 2010, ApJ, 724, 1030
Gordon, K. D., Clayton, G. C., Misselt, K. A., Landolt, A. U., & Wolﬀ, M. J.
2003, ApJ, 594, 279
Kroupa, P. 2001, MNRAS, 322, 231
Lada, C. J., & Lada, E. A. 2003, ARA&A, 41, 57
Ma, J. 2012, AJ, 144, 41
Maíz Apellániz, J. 2006, AJ, 131, 1184
Maíz Apellániz, J. 2009, Ap&SS, 324, 95
Marigo, P., Girardi, L., Bressan, A., et al. 2008, A&A, 482, 883
Massey, P., Olsen, K. A., Hodge, P. W., et al. 2006, in Am. Astron. Soc. Meet.
Abstracts, BAAS, 38, 939
McConnachie, A. W., Irwin, M. J., Ferguson, A. M. N., et al. 2005, MNRAS,
356, 979
Narbutis, D., Vanseviˇcius, V., Kodaira, K., Bridžius, A., & Stonkut˙e, R. 2008,
ApJS, 177, 174
Park, W., & Lee, M. G. 2007, AJ, 134, 2168
Popescu, B., & Hanson, M. M. 2009, AJ, 138, 1724
Popescu, B., & Hanson, M. M. 2010, ApJ, 724, 296
Rosolowsky, E., & Simon, J. D. 2008, ApJ, 675, 1213
San Roman, I., Sarajedini, A., Garnett, D. R., & Holtzman, J. A. 2009, ApJ, 699,
839
San Roman, I., Sarajedini, A., & Aparicio, A. 2010, ApJ, 720, 1674
Santos, Jr., J. F. C., & Frogel, J. A. 1997, ApJ, 479, 764
Sarajedini, A., & Mancone, C. L. 2007, AJ, 134, 447
Schlegel, D. J., Finkbeiner, D. P., & Davis, M. 1998, ApJ, 500, 525
U, V., Urbaneja, M. A., Kudritzki, R.-P., et al. 2009, ApJ, 704, 1120
Vanseviˇcius, V., Kodaira, K., Narbutis, D., et al. 2009, ApJ, 703, 1872
Worthey, G. 1994, ApJS, 95, 107
Pages 8 to 10 are available in the electronic edition of the journal at http://www.aanda.org
A20, page 7 of 10
A&A 550, A20 (2013)
log( / yr)
t

log(
/ M )
m
−
(
)
E B
V
10
9
8
7
log( / yr) from V09
t
log( / yr) from V09
t
10
9
8
7
10
9
8
7
−
=
log( / yr), (
)
[0.04,0.5]
t
E B
V
10
9
8
7
5
4
3
5
4
3

log(
/ M ) from V09
m
5
4
3

log(
/ M ) from V09
m
−
=

log(
/ M ), (
)
[0.04,0.5]
m
E B
V
5
4
3
−
(
) from V09
E B
V
−
(
) from V09
E B
V
−
−
=
(
), (
)
[0.04,0.5]
E B
V
E B
V
0.8
0.4
0
0.4
0.8
0
0.4
0.8
0
0.4
0.8
−
=
(
)
[0.04,0.5]
E B
V
−
=
(
)
[0.04,1.0]
E B
V
−
=
(
)
[0.04,1.0]
E B
V
a)
b)
c)
d)
e)
f)
g)
h)
i)
1
2
1
2
3
3
Fig. 6. M 31: age, mass, and extinction of 211 star clusters from (Vanseviˇcius et al. 2009, as V09). Panels a), d), g) show results when a narrow
extinction range of E(B −V) = [0.04, 0.5] is allowed in the model grid, compared to V09 values. Panels b), e), h) show results for a wider allowed
extinction range [0.04, 1.0], compared to V09 values. Panels c), f), i) compare results obtained in a wide extinction range vs. the ones obtained in
a narrow extinction range. In panels a), b), c), a density map of Fig. 3d is reproduced to show regions of age-extinction degeneracy. Error bars are
computed as described in Sect. 2. Six clusters from V09, which have E(B −V) > 1, are not shown in panels g) and h). Dashed ellipses, numbered
“1”, “2”, and “3”, describe majority of associated clusters in the age and extinction panels.
A20, page 8 of 10
P. de Meulenaer et al.: Deriving physical parameters of unresolved star clusters. I.
−1.0
−0.5
0
0.5
1.0
1.5
−0.5
0
0.5
1.0
1.5
−0.5
0
0.5
1.0
1.5
–1
0
1
2
3
−1.5
a)
b)
−
B
V
−
R
I
−
U
B
−
U
V
Fig. 7. M 33 galaxy star cluster sample of 161 objects from catalog of San Roman et al. (2010) (circles and stars) and the studied sample of 40 ob-
jects (stars) common to Ma (2012) and San Roman et al. (2009). Panels show a) U −B vs. B −V, and b) U −V vs. R −I diagrams. The model
grid (without extinction) used to derive physical parameters of clusters is displayed in the background with indicated reddening vectors following
the LMC extinction law. The continuous line traces PADOVA SSP of Z = 0.008. The B band magnitudes of clusters were shifted by 0.1 mag.
A20, page 9 of 10
A&A 550, A20 (2013)
−
=
(
)
[0.04,1.0]
E B
V
−
=
(
)
[0.04,1.0]
E B
V
−
=
(
)
[0.04,0.3]
E B
V
a)
b)
c)
d)
e)
f)
g)
h)
i)
−
(
) from S09
E B
V
−
(
) from S09
E B
V
−
−
=
(
), (
)
[0.04,0.3]
E B
V
E B
V
9
8
7
log( / yr) from S09
t
log( / yr) from S09
t
9
8
7
9
8
7
−
=
log( / yr), (
)
[0.04,0.3]
t
E B
V
log( / yr)
t
9
8
7
5
4
3

log(
/ M ) from S09
m
5
4
3

log(
/ M ) from S09
m
−
=

log(
/ M ), (
)
[0.04,0.3]
m
E B
V
5
4
3

log(
/ M )
m
5
4
3
0
0.1
0
0.1
0
0.2
0.4
−
(
)
E B
V
0.8
0.4
Fig. 8. M 33: age, mass and extinction of 40 star clusters common to catalogs of Ma (2012) and (San Roman et al. 2009, as S09). Panels a), d), g)
show results when a narrow extinction range of E(B−V) = [0.04, 0.3] is allowed in the model grid, compared to S09 values. Panels b), e), h) show
results for a wider allowed extinction range of E(B −V) = [0.04, 1.0], compared to S09 values. Panels c), f), i) compare results obtained in a wide
extinction range vs. the ones obtained in a narrow extinction range. In panels a), b), c), a density map of Fig. 3d is reproduced to show regions of
age-extinction degeneracy. Error-bars are computed as described in Sect. 2.
A20, page 10 of 10
