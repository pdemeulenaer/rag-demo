VILNIUS UNIVERSITY
CENTER FOR PHYSICAL SCIENCES AND TECHNOLOGY
Philippe de Meulenaer
The accuracy of integrated star cluster
parameters.
The effects of stochasticity
Doctoral Dissertation
Physical sciences, Physics (02 P)
Vilnius, 2015
Doctoral dissertation was completed during 2010–2014 at Vilnius
University.
Scientiﬁc supervisor:
Prof. dr. Vladas Vansevičius (Vilnius University, Physical sciences,
Physics – 02 P)
VILNIAUS UNIVERSITETAS
FIZINIŲ IR TECHNOLOGIJOS MOKSLŲ CENTRAS
Philippe de Meulenaer
Integralinių žvaigždžių spiečių parametrų
tikslumas.
Stochastiniai efektai
Daktaro disertacija
Fiziniai mokslai, ﬁzika (02 P)
Vilnius, 2015
Disertacija parengta 2010–2014 metais Vilniaus universitete.
Mokslinis vadovas:
Prof. dr. Vladas Vansevičius (Vilniaus universitetas, ﬁziniai mokslai,
ﬁzika – 02 P)
Abstract
Star clusters are important tools to probe the star formation mechanisms
and star formation history in their host galaxy. The traditional way to
derive the physical parameters of star clusters using integrated broad-band
photometry makes use of the Simple Stellar Population models (SSP), which
can be considered as oversimpliﬁed. Indeed, these models consider that the
way stellar masses are created in star clusters is by continuously populating
the Initial Mass Function (IMF), which is an idealized view. During the last
forty years, observations have shown that the Initial Mass Function should
be considered as a probability distribution function, according to which
stellar masses are sampled randomly. This has the eﬀect to create diﬀerent
number of massive stars in clusters with the same physical parameters and
hence dispersing the colors of clusters. This results in strong biases when
trying to derive physical parameters of star clusters using oversimpliﬁed
SSP models.
In this thesis, we develop a method of stellar mass sampling which takes
into account the stochasticity due to the fact that the IMF is a probability
distribution function, which allows us to reproduce the dispersion of star
cluster integrated colours. A model grid is built to reproduce all possible
choices of physical parameters (age, mass, extinction, and metallicity). We
also built a method to derive these parameters, comparing the integrated
colors of observed clusters to the ones of our model grid. The method is
tested on artiﬁcial models, to derive its accuracy. We show that the deriva-
tion of parameters, such as metallicity, is possible under good photometric
conditions that we quantify. We also compare the derivation of star cluster
parameters using diﬀerent photometric systems, and show that the photo-
metric systems containing ultraviolet passbands are privileged for a best
determination of parameters such as age or metallicity.
We apply the method on diﬀerent star cluster catalogs of the two major
Local Group galaxies: M31 and M33. For a M31 star cluster catalog with
Hubble Space Telescope (HST) broad-band photometry, we show in the
case of bright clusters that the metallicity derivation is consistent with
5
spectroscopic values derived independently in the literature. For the M33
star cluster sample, we merge optical broad-band catalogs available from
the literature and add near-infrared data that we derive from deep Two
Micron All Sky Survey (2MASS) images. We then derive the age, mass,
and extinction of the clusters. Clusters overlapping with previous study
in the literature, for which age and mass have been derived using resolved
photometry from the HST, are found to have parameters in good agreement.
We also provide general properties of the M33 star cluster system such as
the typical disruption rate of the clusters.
6
Acknowledgments
A PhD thesis is rarely the fruit of the work of a single person, but it includes
the contribution of many people. Here I would like to express my gratitude
to these many people who helped me in so many ways before and during
this thesis. I thank very much Dominique Lambert and Gregor Rauw for
supporting me during the search of this doctoral position, and the Dean of
Vilnius University Physics Faculty for welcoming and helping me eﬃciently
to enter in the Astronomical Observatory.
I thank colleagues from the Astronomical Observatory for their kind
support throughout these four years: Jokubas Sūdžius, Julius Sperauskas,
Stanislava Bartašiutė, Arūnas Kučinskas, Audrius Bridžius, Viktoras De-
veikis, Saulius Raudeliūnas, Kastytis Zubovas, as well as students Kostas
Sabulis and Rokas Naujalis. I also enjoyed fruitful scientiﬁc interactions
with Nate Bastian, Mark Gieles, Pavel Kroupa, Leo Girardi.
I also wish to thank warmly my colleagues Donatas Narbutis and Tadas
Mineikis; the advices and precious help that they constantly brought me
made this doctoral study a pleasant working time. I should particularly
thank Tadas for dedicating so much time to help me when I was struggling
with details of the lithuanian language and institutions.
I am indebted to my supervisor Vladas Vansevičius for his teaching, his
constant support, and his patience, as it was not easy to have a foreigner
student. His wide and deep view in science inspired me in many ways during
the thesis, and will certainly continue to have a great impact on the rest of
my scientiﬁc career.
Merci à toute ma famille pour l’aﬀection et les encouragements que vous
m’avez donnés au jour le jour. Merci spécialement à Papa pour son enthou-
siasme formidable, et Maman pour sa tendresse, vous m’avez tout donné.
Dėkoju savo žmoną, Eglė, už nuolatinį palaikimą ir meilę, ir savo dukrą,
Liucija, už sitą nuolatinį džiaugsmą tave laikyti rankose.
“Ce que Dieu a caché aux sages et aux savants, Il l’a révélé aux
pauvres et aux tous petits.” (Mt 11, 25)
7
8
Contents
Abstract
5
Acknowledgments
7
Contents
10
Introduction
11
Motivation
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
11
Aims of the study . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
13
Main tasks
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
13
Results and statements to defend . . . . . . . . . . . . . . . . . . . . .
13
Publications on thesis topic in refereed journals . . . . . . . . . . . . .
14
Other publications in refereed journals . . . . . . . . . . . . . . . . . .
14
Conference publication on thesis topic
. . . . . . . . . . . . . . . . . .
14
Presentations at conferences on thesis topic
. . . . . . . . . . . . . . .
15
Personal contribution . . . . . . . . . . . . . . . . . . . . . . . . . . . .
15
Thesis outline . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
16
1
Star Cluster Models
17
1.1
SSP models for unresolved star clusters: Failure and need of more
elaborated models
. . . . . . . . . . . . . . . . . . . . . . . . . .
17
1.1.1
The Simple Stellar Population models: deﬁnition . . . . .
17
1.1.2
The degeneracy problem . . . . . . . . . . . . . . . . . . .
18
1.1.3
The stochasticity problem . . . . . . . . . . . . . . . . . .
18
1.2
Stochastically sampled star cluster models . . . . . . . . . . . . .
20
1.3
The Reduced Random Sampling Method . . . . . . . . . . . . . .
26
1.3.1
Introduction to the Reduced Random Sampling idea
. . .
26
1.3.2
Presentation of the method of Reduced Random Sampling
27
1.3.3
Calibration of the Reduced Random Sampling . . . . . . .
33
1.3.4
Summary: the Reduced Random Sampling . . . . . . . . .
35
1.4
Model grid for age, mass, extinction, and metallicity
. . . . . . .
36
2
Deriving the Cluster Parameters
39
2.1
The method of star cluster parameters derivation . . . . . . . . .
39
2.2
Improvement on the derivation of parameters
. . . . . . . . . . .
41
2.3
Test of the method with an artiﬁcial cluster sample . . . . . . . .
45
2.3.1
Is it possible to reduce the age-extinction degeneracy?
. .
47
2.4
Metallicity eﬀects: one–metallicity vs one–metallicity . . . . . . .
49
2.4.1
Parameter derivation for artiﬁcial clusters in UBV RI . . .
49
9
2.4.2
Addition of near-infrared passbands: UBV RI + JHK
. .
53
2.4.3
Addition of ultraviolet passbands: GALEX + UBV RI
. .
53
2.5
Metallicity eﬀects: one–metallicity vs whole metallicity range . . .
55
2.6
Exploration of the metallicity eﬀects for the WFC3 photometric
system onboard HST . . . . . . . . . . . . . . . . . . . . . . . . .
63
2.6.1
One–metallicity vs one–metallicity test . . . . . . . . . . .
63
2.6.2
One–metallicity vs whole metallicity range: taking metalli-
city eﬀects into account
. . . . . . . . . . . . . . . . . . .
64
3
Application to real Star Clusters
67
3.1
The M31 galaxy star cluster sample of Vansevičius et al. (2009) .
67
3.2
The M31 galaxy star cluster sample of PHAT survey
. . . . . . .
71
3.2.1
Results with ﬁxed solar metallicity . . . . . . . . . . . . .
73
3.2.2
Results with free metallicity . . . . . . . . . . . . . . . . .
74
3.3
Application to the M33 star clusters
. . . . . . . . . . . . . . . .
79
3.3.1
Why M33?
. . . . . . . . . . . . . . . . . . . . . . . . . .
79
3.3.2
The M33 star cluster catalog
. . . . . . . . . . . . . . . .
80
3.3.3
Artiﬁcial tests . . . . . . . . . . . . . . . . . . . . . . . . .
89
3.3.4
The derived physical parameters of the M33 star clusters .
94
Conclusions
103
References
104
10
Introduction
Motivation
Star clusters are considered to be the building bricks of galaxies in the sense
that most of their stars are believed to be born within star clusters. As a
consequence, their study allows a better understanding of the history of the
star formation in their host galaxy. They could also be used as constraints
for galaxy formation models.
The aim of this work is to help solving two major problems faced by
scientists in the attempt to recover the physical parameters of star clusters
(age, mass, extinction, and metallicity), especially when they are observed
in other galaxies, such as the Local Group Andromeda (M31) and Trian-
gulum (M33) galaxies, with integrated broad-band photometry. The ﬁrst
issue comes from the fact that, in integrated broad-band photometry, clus-
ters with diﬀerent parameters may have similar integrated colors, an eﬀect
referred to as parameter degeneracy.
The second reason preventing accurate derivation of cluster parameters
is due to the probabilistic (stochastic) sampling of star masses in star clus-
ters. The stochastic sampling of star masses causes the ﬂuctuation of the
number of bright stars for clusters with the same age, mass, extinction, and
metallicity, and hence results in diﬀerent integrated luminosities and co-
lors for clusters. When trying to derive the cluster parameters, this eﬀect,
stronger in the case of young and low-mass clusters, introduces very often
strong biases on the cluster parameters, that might be far larger than the
ones due to photometric uncertainties.
The traditional way to derive the physical parameters of star clusters
using integrated broad-band photometry makes use of the Simple Stellar
Population models (SSP), which consider that the way stellar masses are
created in star clusters is by continuously populating the Initial Mass Func-
tion (IMF). This means that these models are oversimpliﬁed because they
do not take into account the stochastic sampling of star masses happening
during the birth of clusters. When modeling the stochastic sampling of star
11
masses in clusters, the physical parameters of the clusters are much better
derived than by use of the SSP models, because modeling the stochastic
sampling allows a better reproduction of the integrated color distributions
of star clusters.
Hence, the derivation of star cluster parameters using
SSP models should be abandoned in favor of the more realistic modeling of
stochastically sampled star clusters.
This thesis is motivated by the need to derive as best as possible the
parameters of many star clusters and use eﬃciently the ever growing high-
quality amount of observations gathered using ground based or space tele-
scopes. The accuracy of our parameter derivation method has been eval-
uated using artiﬁcial star clusters in diﬀerent photometric systems.
We
applied the method to derive the physical parameters of populations of star
clusters from the M31 and M33 galaxies.
12
Aims of the study
Study the inﬂuence of the stochasticity eﬀects on the accuracy of star cluster
parameters (age, mass, extinction, and metallicity) derivation.
Main tasks
1. Build the method of sampling of star clusters stellar masses allowing
to mimic the stochasticity of star clusters integrated photometry.
2. Build the method of automatic comparison of integrated photometry
of the star cluster models to observed star clusters, to derive their
parameters.
3. Determine the accuracy of the method for diﬀerent photometric sys-
tems
4. Apply the method of cluster parameter derivation on real star clusters
of M31 and M33.
Results and statements to defend
1. The method of derivation of star cluster parameters, which takes into
account the stochastic sampling of star masses, allows a better deriva-
tion of the age, mass, extinction, and metallicity, compared to tradi-
tional methods, based on Simple Stellar Population models.
2. The method makes possible the derivation of star cluster metallicity
based on broad-band photometry in optical and ultraviolet passbands,
in the case of small photometric errors: ≤0.05 mag in optical and
≤0.15 mag in ultraviolet passbands.
3. Using a sample of star clusters of the M31 galaxy, we demonstrated the
importance of the metallicity eﬀects when trying to derive the other
parameters.
4. The age, mass, and extinction parameters have been derived for a
catalog of star clusters of the M33 galaxy, the typical disruption time
13
of clusters in the M33 galaxy is ∼300 Myr and is comparable to the
disruption time of clusters in M31 galaxy.
Publications on thesis topic in refereed journals
1. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving phys-
ical parameters of unresolved star clusters. I. Age, mass, and extinction
degeneracies, Astronomy and Astrophysics, 2013, 550, A20
2. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving phys-
ical parameters of unresolved star clusters. II. The degeneracies of age, mass,
extinction, and metallicity, Astronomy and Astrophysics, 2014, 569, A4
3. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Stochasticity
in star clusters: Reduced Random Sampling Method, Baltic Astronomy,
2014, 23, 199
4. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving phys-
ical parameters of unresolved star clusters. III. Application on M31 PHAT
clusters, Astronomy and Astrophysics, 2015, 574, A66
5. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving phys-
ical parameters of unresolved star clusters. IV. The M33 star cluster system,
Astronomy and Astrophysics (accepted)
Other publications in refereed journals
1. de Meulenaer P., Carrier F., Miglio A., Bedding T. R., Campante T.,
Eggenberger P., Kjeldsen H., Montalban J., Core properties of Alpha Cen-
tauri A using asteroseismology, Astronomy and Astrophysics, 2010, 523,
54
2. Narbutis D., Semionov D., Stonkutė R., de Meulenaer P., Mineikis T.,
Bridžius A., Vansevičius V., Deriving structural parameters of semi-resolved
star clusters I. Program for crowded ﬁelds - FitClust, Astronomy and As-
trophysics, 2014, 574, A30
3. Narbutis D., Stonkutė R., de Meulenaer P., Mineikis T., Vansevičius V.,
Structural Parameters of Star Clusters: Stochastic Eﬀects, Baltic Astron-
omy, 2014, 23, 103
Conference publication on thesis topic
1. de Meulenaer P., D. Narbutis, T. Mineikis, V. Vansevičius, Stochastic-
ity eﬀects on derivation of physical parameters of unresolved star clusters,
Memorie della Societa Astronomica Italiana, 2013, v.84, p.204
14
Presentations at conferences on thesis topic
1. de Meulenaer P., Narbutis D., Vansevičius V., Physical parameters of
star clusters: stochasticity and degeneracies, “39 Lietuvos nacionalinė ﬁzikos
konferencija”, 2011 October 6-8, Vilnius, Lithuania (poster presentation)
2. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Stochastic-
ity eﬀects on derivation of physical parameters of unresolved star clusters,
“Reading the book of globular clusters with the lens of stellar evolution”,
Roma, Italy, November 26-28 d. 2012 (poster presentation)
3. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Star cluster
parameters from integrated photometry: The case of WFC3@HST. Confer-
ence “European Week of Astronomy and Space Science” 2013 July 12-16,
Turku, Finland (oral presentation)
4. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Star cluster
parameters from integrated photometry: The case of WFC3. Conference
“Evolution of Star Clusters: From Star Formation to Cosmic Ages (An-
nual Meeting of the Astronomische Gesellschaft)” 2013 September 24-27,
Tübingen, Germany (poster presentation)
5. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving phys-
ical parameters of unresolved star clusters: age-mass-extinction-metallicity
problem, “Multiwavelength-surveys: Galaxy Formation and Evolution from
the early universe to today”, 2014 May 12-16, Dubrovnik, Croatia (poster
presented by Narbutis D.)
6. Narbutis D., de Meulenaer P., Stonkutė R., Mineikis T., Vansevičius
V., Stochastic Eﬀects in Star Clusters, “Resolved and unresolved stellar
populations”, 2014 October 13-17, Garching, Germany (poster presented by
Narbutis D.)
7. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving phys-
ical parameters of unresolved star clusters in the M33 galaxy, “41 Lietuvos
nacionalinė ﬁzikos konferencija”, 2015 June 17-19, Vilnius, Lithuania (oral
presentation)
Personal contribution
The author imagined and developed with the help of the publication co-
authors a new method, which takes into account the stochastic sampling of
star masses in star clusters, aimed to derive the cluster parameters. The
co-authors participated in the interpretation of scientiﬁc results and the
preparation of the publications. The author performed all the program-
ming works, the artiﬁcial tests of the method, and the derivation of the
parameters of star clusters from the M31 and M33 galaxies. In the publi-
15
cations on the thesis topic, the contribution of the author is no lower than
70%.
Thesis outline
The dissertation consists of an Introduction, three Chapters, Conclu-
sions, and the References.
Chapter 1 introduces to the problem of stochasticity in star clusters.
It is shown that the traditional Simple Stellar Population models are unﬁt
to derive evolutionary parameters of star clusters. A grid of models taking
stochastic sampling is built for the four star cluster parameters (age, mass,
extinction, and metallicity).
Chapter 2 develops the method to derive the star cluster physical pa-
rameters taking into account the stochasticity problem.
The method is
tested on artiﬁcial star cluster samples. By use of diﬀerent photometric
systems, we demonstrate that the ultraviolet associated with optical is best
suited for the break of degeneracies between clusters parameters.
Chapter 3 applies the method of cluster parameter derivation on real
star cluster samples from two major Local Group galaxies, M31 and M33.
In M31, we use the photometric catalog from a survey performed with the
Hubble Space Telescope to derive the cluster parameters, including metalli-
city, and hence to show the metallicity eﬀects on accuracy of the derivation
of the other parameters. In M33, we merge most recent ground-based op-
tical catalogs and supplement near-infrared data to derive the parameters
(age, mass, and extinction for all clusters, and metallicity for old ones only)
of this galaxy star cluster population and constrain the rate of evolutionary
fading and disruption of clusters in the tidal ﬁeld of the galaxy.
16
Chapter 1
Star Cluster Models
1.1
SSP models for unresolved star clusters:
Failure and need of more elaborated models
1.1.1
The Simple Stellar Population models: deﬁnition
In his seminal work, Salpeter (1955) was the ﬁrst to quantify the distribution
of the stellar Initial Mass Function (IMF), with a simple power-law of index
−2.35. This function, ϕ(m), describes how many stars of given mass m
one expects depending on the mass m of the star. It essentially indicates
that massive stars are much less likely than low-mass stars in a stellar
population.
More recently, the shape of the IMF has been found to be
composed of several power-laws (Kroupa 2001), as deﬁned in Eq. 1.2 and
shown in Fig. 1.3 (a).
Isochrones are models computed for stars of same age t and metallicity
[M/H], and for all masses between a lower mass ml and an upper mass mu.
In the isochrones used in this thesis, based on the PADOVA stellar models
(Marigo et al. 2008; Girardi et al. 2010), ml = 0.01 M⊙and mu = 120 M⊙.
These models give the ﬂux fA(m, t, [M/H]) or magnitude MA(m, t, [M/H])
for any given photometric passband A.
From the IMF and the isochrones, we can build the concept of “Simple
Stellar Population” (SSP). Indeed, stars of a stellar population following the
SSP models are born at the same time and from the same progenitor giant
molecular cloud, giving them the same properties: same age, metallicity,
and distance to the observer (hence the same amount of extinction). The
masses of the stars are built by continuously sampling the IMF. Hence, for a
given photometric passband A, the integrated magnitude of the SSP model
is (see, e.g., Salaris & Cassisi 2006):
17
MA(t, [M/H]) = −2.5 log10
( ∫mu
ml
10−0.4 MA(m′,t,[M/H]) ϕ(m′) dm′
)
.
(1.1)
The traditional photometric method used to derive the star cluster phys-
ical parameters is based on the comparison of the predicted integrated mag-
nitudes MA(t, [M/H]) of a set of Simple Stellar Population (SSP) models of
diﬀerent ages and metallicities with the integrated broad-band photometry
of the observed clusters, as reported, e.g., Anders et al. (2004) and Bridžius
et al. (2008)(see also Narbutis et al. 2007). However, this method is strongly
biased by degeneracies between parameters and by the stochastic presence
of bright stars that dominate the integrated photometry. These problems
are presented below.
1.1.2
The degeneracy problem
In the SSP models shown in the color-color diagram in Fig. 1.1, built for 13
diﬀerent metallicities in the range [M/H] = 0.2 (reddest line) to −2.2 (bluest
line), one can see that various degeneracies are present.
Indeed, rather
young star clusters of high metallicity can easily be mixed with older and
lower metallicity clusters (see, for example, the region U −B ∼0 and B −
V ∼0.2). If we add extinction, the SSP models at a given position are hence
allowed to be degenerated with all other models situated in the direction of
the arrow, creating an age-extinction degeneracy for models situated on the
same SSP, or an age-extinction-metallicity for models situated on diﬀerent
SSPs.
1.1.3
The stochasticity problem
Many studies in the literature have used the SSP models to derive star
cluster physical parameters (age, mass, extinction, and metallicity). How-
ever, several recent studies (e.g.
Santos & Frogel 1997; Deveikis et al.
2008; Fouesneau & Lançon 2010) have brought attention on the fact that
these models with continuously sampled IMF, which are unphysical, are
oversimpliﬁed and biased:
• They are oversimpliﬁed because they do not take the natural disper-
18
0.2
0.0
0.2
0.4
0.6
0.8
1.0
B−V
1.0
0.5
0.0
0.5
U−B
Fig. 1.1.
SSPs models
from
PADOVA
(Marigo
et al. 2008; Girardi et al.
2010)
for
13
diﬀerent
metallicities in the range
[M/H] = 0.2 (reddest line)
to -2.2 (bluest line). The
arrow indicates the extinc-
tion direction, for AV =
1 mag.
sion of integrated colors of star clusters into account, the so-called
stochasticity problem. In reality, the masses of stars are stochasti-
cally sampled following the stellar IMF, and the latter could be seen
as a probability distribution function (Santos & Frogel 1997). Hence,
two clusters with the same physical parameters could host a diﬀerent
number of massive bright stars, resulting in very diﬀerent integrated
colors, especially in the case of young and low-mass clusters which
contain only few massive bright stars. This will be shown in details in
the next Section, as well as in Fig. 1.5.
• SSP models are biased because they do not even match the av-
erage of integrated color distributions for star cluster with mass1
log10(M/M⊙) ≲4 (see, e.g.,
Fouesneau & Lançon 2010; Popescu
& Hanson 2010; Silva-Villa & Larsen 2011).
As a consequence, the derivation of star cluster parameters using the SSP
models can lead to severe biases, as was demonstrated by Fouesneau &
Lançon (2010) (see their Fig. 3) by use of artiﬁcial tests.
1In the whole dissertation, m indicates the mass of stars, while M indicates the mass of
clusters.
19
7
8
9
10
log10(t=yr) true
7
8
9
10
log10(t=yr) derived
a)
3
4
5
log10(M=M ¯) true
2
3
4
5
log10(M=M ¯) derived
b)
0.2
0.6
1.0
E(B¡V) true
0.2
0.6
1.0
E(B¡V) derived
c)
7
8
9
10
log10(t=yr) true
7
8
9
10
log10(t=yr) derived
d)
3
4
5
log10(M=M ¯) true
2
3
4
5
log10(M=M ¯) derived
e)
0.2
0.6
1.0
E(B¡V) true
0.2
0.6
1.0
E(B¡V) derived
f)
Fig. 1.2.
SSP vs stochastic method of derivation of the physical parameters of an
artiﬁcial star cluster sample with metallicity [M/H] = 0.
New models (Fouesneau & Lançon 2010; Popescu & Hanson 2010; da
Silva et al. 2012; de Meulenaer et al. 2013, 2014a, 2015a,b, hereafter Papers
I, II, III, & IV) take into account this natural dispersion of integrated colors
due to the star mass stochastic sampling and allow to derive the cluster
parameters in a more realistic way, avoiding the strong biases of the SSP
method.
As an example, we show in top panels of Fig. 1.2 the derivation of age,
mass, and extinction parameters using SSP models of realistic artiﬁcial
clusters, simulated using a stochastic sampling of the IMF that will be
developed in the next Section. In bottom panels, we show for comparison
the derivation of the star cluster parameters using a method that takes
stochastic sampling into account, developed in Section 2.1.
1.2
Stochastically sampled star cluster models
Historically, the ﬁrst mention of stochastic sampling of star masses in star
clusters has been introduced by Barbaro & Bertelli (1977), as they pointed
out that diﬀerent numbers of post main sequence stars may results in very
diﬀerent integrated properties of star clusters than predicted from the SSP
20
models. They already stated that the description of the integrated color
distributions of clusters cannot be performed analytically and should be
done by stochastically sampling the IMF. Later cluster studies (e.g. Chiosi
et al. (1988) for LMC clusters, Lançon & Mouhcine (2000)) also stressed
the importance of taking into account the dispersion of integrated colors of
clusters due to stochastic sampling when trying to derive their evolutionary
parameters.
Santos & Frogel (1997) (see also Cerviño et al. 2002; Cerviño & Luridiana
2004; Deveikis et al. 2008) provided a scheme of the stochastic sampling on
which is based the method of cluster sampling used in this thesis.
To sample the star masses in a star cluster, the IMF can be considered
as a probability distribution function (PDF) that is sampled randomly be-
tween the highest and the lowest star masses. Contrarily to SSP models,
this results in sampling discretely the star masses in the IMF, and not con-
tinuously. The stochasticity is introduced in the fact that bright stars are
populated more sparsely than lower-brightness stars. Due to the random
sampling naturally resulting in a diﬀerent number of bright stars, the inte-
grated colors of two clusters with the same physical parameters (same age,
mass, extinction, and metallicity) turn out to be very diﬀerent, and can
also be very diﬀerent from the SSP prediction.
Mathematically, here is the procedure of the sampling of the star cluster
star masses, which is also illustrated in Fig. 1.3. We use the Kroupa (2001)
IMF (shown in Fig. 1.3 a), deﬁned as:
ϕ(m) = k · Ci · m−αi















α0 = 0.3,
if m ∈[m0, m1],
α1 = 1.3,
if m ∈[m1, m2],
α2 = 2.3,
if m ∈[m2, m3],
α3 = 2.3,
if m ∈[m3, m4],
(1.2)
where m0 = 0.01M⊙, m1 = 0.08M⊙, m2 = 0.5M⊙, m3 = 1M⊙, m4 =
150M⊙, the highest physical stellar mass limit, and k and Ci are the normal-
ization constants. We then introduce the cumulative distribution function
21
2
1
0
1
2
log10(m/M ⊙)
6
4
2
0
2
log10(φ(m))
a)
2
1
0
1
2
log10(m/M ⊙)
0.0
0.2
0.4
0.6
0.8
1.0
nCDF(m)
b)
Fig. 1.3. Scheme of the Random Sam-
pling. Panel (a) shows the IMF, which
is the probability distribution function
of the sampling of star masses. From
the IMF, the cumulative distribution
function of the number of stars, nCDF,
is built in panel (b) using Eq. 1.4. Ran-
dom numbers are drawn uniformly in
the range [0,1] and transformed into
mass by inverting the nCDF relation,
as emphasized by the black arrows for
two given random numbers.
2
1
0
1
2
log10(m/M ⊙)
10-6
10-4
10-2
100
102
φ(m)
c)
of the number of stars, nCDF, as:
nCDF(mlow, m) =
∫m
mlow
ϕ(m′)dm′ ,
(1.3)
which gives the number of stars contained in the cluster between the lowest
mass mlow to a given mass m.
Using the IMF deﬁned above, it is possible to derive the analytical ex-
pression of the nCDF:
nCDF(mlow, m) =
i−1
∑
j=0
kCj
1 −αj
[m1−αj
j+1 −m1−αj
j
] +
kCi
1 −αi
[m1−αi −m1−αi
i
] ,
(1.4)
where i is deﬁned by m ∈[mi, mi+1] in Eq. 1.2.
22
Fig. 1.4. Here we show two realizations of star clusters (in white and in gray)
for each of three diﬀerent cluster masses, log10(M/M⊙) = 3, 4, and 5. For each
ﬁxed mass, the two clusters generated display a diﬀerent number of massive stars,
which are shown in the color-magnitude diagrams in bottom panels, which are
built for the age log10(t/yr) = 7. The vertical lines in panels (a)–(f) is the limit
after which stars vanish due to stellar evolution.
Knowing exactly the nCDF for any star mass m in the range [m0, m4],
which is shown in Fig. 1.3 (b), it is now possible to sample it uniformly
between its lowest value, 0, corresponding to the minimal mass m0, and
the highest value, 1, corresponding to the maximum mass m4. As shown
in panel (b), once the y-axis is sampled, we can use the expression of the
nCDF to project the samples on the x-axis and hence to derive the masses
m associated to each random number generated. This procedure is repeated
for all stars until the cluster target mass is reached by summing all the
23
0.0
0.5
1.0
1.5
B¡V
−1.0
−0.5
0.0
0.5
1.0
U¡B
a)
0.0
0.5
1.0
1.5
B¡V
−1.0
−0.5
0.0
0.5
1.0
U¡B
b)
0.0
0.5
1.0
1.5
B¡V
−1.0
−0.5
0.0
0.5
1.0
U¡B
c)
Fig. 1.5.
Groups of 1000 clusters with
ﬁxed physical parameters, to illustrate the
dispersion of integrated colors and the ef-
fect of diﬀerent age and mass on these
dispersions. The parameters are ﬁxed to
log10(t/yr) = 7, 8, 9, 10, log10(M/M⊙) =
3 (in blue), 4 (in green), or 5 (in red), and
[M/H] = 0 (panel a), -0.6 (panel b), or -2
(panel c). SSP of corresponding metallic-
ities are also shown (dashed lines). Error
bars are typical errors of 0.05 mag in each
passband.
generated masses of stars. In the following, this method is referred to as
Random Sampling. Fig. 1.3 (c) shows the resulting sampled mass function
of the generated star cluster, compared to the IMF according to which the
stars have been randomly sampled.
The Random Sampling aﬀects especially the integrated photometry of
low-mass clusters. Indeed, as shown in Fig. 1.4, two generated low-mass
clusters will harbor a diﬀerent number of massive stars, and hence a diﬀerent
integrated photometry, while for massive clusters this eﬀect will be almost
negligible because they will be populated by many massive stars. Indeed,
the more massive the mass of the cluster, the more populated will be the
cluster in stars, and so the diﬀerence in the sampling becomes negligible for
massive star clusters.
Fig. 1.5 illustrates how the stochasticity aﬀects the integrated colors de-
pending on their age, mass, and metallicity, for a few groups of clusters.
24
Each of the group is composed of 1000 clusters with the same physical pa-
rameters: the age is ﬁxed to log10(t/yr) = 7, 8, 9, 10 (shown in the picture),
to log10(M/M⊙) = 3 (in blue), 4 (in green), or 5 (in red), and [M/H] = 0
(panel a), -0.6 (panel b), or −2 (panel c). As shown in the ﬁgure, the SSP
models (dashed lines) are consistent with the centers of the distributions
only for massive clusters, log10(M/M⊙) = 5.
At ﬁxed mass and metallicity, for example for log10(M/M⊙) = 3 and
[M/H] = 0 (panel a, the blue distributions), the eﬀect of the age can be seen
by the contraction of the blue distributions when age gets older (from top to
bottom right). The blue and red supergiant stars present at log10(t/yr) = 7
(upper blue distribution) generate a strong stochasticity in the integrated
colors, but they die fast afterwards, and the extent of older distributions
decrease.
At ﬁxed age and metallicity, for example for log10(t/yr) = 7, and
[M/H] = 0 (panel a, the upper blue, green, and red distributions), the
eﬀect of the mass is visible as a contraction of the distributions when the
mass of clusters gets higher. This is simply because the IMF is more densely
sampled. By sampling inﬁnitely the IMF with star masses, one would hence
get the SSP positions in the color-color diagram.
The metallicity eﬀect, from the panel (a) to the panel (c), is illustrated by
a change of the positions of the groups. This can be already seen using SSP
models, as in Fig. 1.1, where the most metallic SSP (reddest line) extends
much more in the red direction, in the U −B versus B −V diagram, than
the SSP with lowest metallicity (blue line).
In Section 1.3, we present a reﬁnement of the Random Sampling, the
Reduced Random Sampling method. Indeed, it is believed that the extent
of stochasticity in the sampling of star mass in clusters may be lower than
the Random Sampling, which would be an upper limit, but still contain
more stochasticity than the Optimal Sampling (Kroupa et al. 2013), which
states that star masses are built deterministically2.
2The Optimal Sampling states that the mass of the most massive star is deterministically
linked to the mass of the cluster, the mass of the second star to the mass of the ﬁrst star, and
so on recursively all the star masses are built. This method is also presented in the Section 1.3.
25
1.3
The Reduced Random Sampling Method
This Section, which has been the object of a paper (de Meulenaer et al.
2014b), contributes to the debate existing nowadays between the two ex-
treme proposed schemes on the way stellar masses are sampled within star
clusters, which are the Optimal Sampling and the Random Sampling of
stellar masses. We propose a new method of sampling of stellar masses
which allows a continuous transition between the Optimal Sampling and
the Random Sampling of star clusters.
We use a sample of young star
clusters available in the literature to calibrate the amount of stochasticity
generated by the proposed method.
1.3.1
Introduction to the Reduced Random Sampling idea
The aim of this Section is to tackle the problem of the inﬂuence of the stellar
mass sampling in star clusters on the stochasticity of their integrated colors.
Indeed, it is still undeﬁned how the stellar masses should be sampled from
the initial mass function (IMF). On one hand, several studies (e.g., Santos
& Frogel 1997, Deveikis et al. 2008, Fouesneau & Lancon 2010) implement
a random stellar mass sampling from the IMF. In this view, the IMF is
seen as a probability density function, according to which stellar masses are
randomly drawn. This is referred to as Random Sampling (RS). On the
other hand, other studies (e.g., Weidner et al. 2010, Weidner et al. 2013,
Kroupa et al. 2013) propose the idea that the stellar masses could be an
Optimal Sampling (OS) of the IMF. In that view, the mass of the most
massive star is exactly determined by the mass of the zero-age star cluster
(Kroupa & Weidner 2003; Pﬂamm-Altenburg et al. 2007; Weidner et al.
2010). Then the mass of the second most massive star is related to the mass
of most massive one, the mass of the third star to the mass of the second,
and so on recursively all stellar masses are generated (see equations 9–11
of Kroupa et al. 2013 for details of the Optimal Sampling scheme). Hence,
for a given star cluster, there is a deterministic link between the masses
of its stars and the cluster’s mass. This view is supported by observations
of the most massive stars of very young clusters (see compilation of such
observations in Weidner et al. 2013) where a trend between the mass of the
most massive stars and the mass of their host clusters seems to exist.
26
In this Section, we present a new sampling method, referred to in the
following as a Reduced Random Sampling (RRS), which can be seen as a
continuous transition between the two extremes that are the RS and the
OS. The idea of the method is to allow a two-parameters variation to tune
the extent of stochasticity that can be decreased to zero-stochasticity (i.e.,
OS) or increased up to full stochasticity (i.e., RS). Then the compilation of
young clusters of Weidner et al. (2013) is used to constrain the best value
of the parameter guiding the extent of stochasticity.
1.3.2
Presentation of the method of Reduced Random
Sampling
Recently, Popescu & Hanson (2014) presented a sampling method based
on the Optimal Sampling (OS). In their method, the mass bins are deﬁned
around each stellar masses derived from Kroupa et al. (2013) OS method, so
that the stars are resampled in these bins, introducing a small stochasticity
in the mass function. However, one could argue that in this process, the
amount of stochasticity is not constrained by observations.
Here we propose a new sampling method, the Reduced Random Sampling,
schemed in Fig. 1.6, which can be considered as a continuous transition
between the OS and the Random Sampling (RS). Here we mention the four
main steps, that we develop in the following:
1. Generate stellar masses using the OS for a star cluster model of given
mass.
2. Deﬁne bins around the masses of OS generated stars.
3. Expand or shrink the bin widths by a deﬁned expansion factor value,
P. For bins deﬁned in step 2, P = 1. When bins are expanded, P > 1,
when bins are shrunk, P < 1.
4. Resample the mass of the star within the modiﬁed bin deﬁned around
it.
The eﬀect of the P factor, controlling the width of the bins is illustrated
in Fig. 1.6 (P is speciﬁed on tops of panels). If we shrink the sizes of the
mass resampling bins (P →0), as sketched in the ﬁrst column of panels in
27
2
1
0
1
2
log10(m/M ⊙)
0.0
0.5
1.0
nCFD(m)
P →0
a)
2
1
0
1
2
log10(m/M ⊙)
6
4
2
0
2
log10(φ(m))
e)
2
1
0
1
2
log10(m/M ⊙)
P = 2
b)
2
1
0
1
2
log10(m/M ⊙)
f)
2
1
0
1
2
log10(m/M ⊙)
P = 6
c)
2
1
0
1
2
log10(m/M ⊙)
g)
2
1
0
1
2
log10(m/M ⊙)
P →∞
d)
2
1
0
1
2
log10(m/M ⊙)
h)
1
2
3
4
5
log10(M/M ⊙)
0
1
2
log10(mmax/M ⊙)
i)
0.0
0.4
0.8
B−V
0.2
0.2
0.6
1.0
U−B
m)
1
2
3
4
5
log10(M/M ⊙)
j)
0.0
0.4
0.8
B−V
n)
1
2
3
4
5
log10(M/M ⊙)
k)
0.0
0.4
0.8
B−V
o)
1
2
3
4
5
log10(M/M ⊙)
l)
0.0
0.4
0.8
B−V
p)
Fig. 1.6. Scheme of the Reduced Random Sampling method, allowing a continuous
transition between the Optimal Sampling (OS) and the Random Sampling (RS).
The columns of panels present results obtained with diﬀerent values of expansion
factors, P, shown on the top of panels. The ﬁrst two rows of panels present the
cumulative distribution function and the IMF respectively. These panels describe
the transition between the OS and the RS, schemed for 2 stars, one in the low-
mass regime and another in the high-mass regime of the IMF. For each stellar
mass built by the OS, a bin is deﬁned around the mass of the star. For purpose
of illustration, the bin in the low-mass regime has been enlarged by a factor 200
in linear scale. In these mass bins, the stellar masses are resampled. The third
row presents the relation between the mass of the most massive stars vs the mass
of their host clusters compared to the Weidner et al. (2013; green solid line) and
Kroupa et al. (2013; cyan long-dashed line) relations. The oblique black dashed
line is the identity relation between the mass of the most massive stars and the
mass of the host clusters, mmax = M, and the horizontal black dashed line is
the physical upper limit of massive stars, 150 M⊙. In fourth row, the impact of
the increase of the stochasticity in the cluster stellar mass sampling on the color
distributions of these cluster models is shown. The cluster models shown have
mass log10(M/M⊙) = 4, with age log10(t/yr) = 7, 8, 9 (blue, orange, red).
28
Fig. 1.6, no stochasticity is produced; it is the Optimal Sampling case. On
the contrary, if we expand the bins two times (P = 2, second column of
panels in Fig. 1.6), we generate stellar masses which are close to the ones of
OS, hence with small stochasticity in the mass function. If we expand more
the mass resampling bins, as sketched in third column of panels in Fig. 1.6
(P = 6), we allow the stellar masses to be resampled further from the
masses given by the OS, resulting in enhanced stochasticity. By expanding
the mass resampling bins very widely, the method then reaches RS (the last
column of panels in Fig. 1.6).
In Fig. 1.6 the impact of shrink and expansion of the mass resampling
bin can be seen on the scatter of the most massive stellar mass versus the
mass of the host star cluster (third row of panels) and on the distribution
of the integrated colors of these star clusters (last row of panels). The bin
expansion increases stochasticity in the integrated photometry of clusters.
In step 1, Stellar masses are ﬁrst optimally sampled using the method of
Kroupa et al. (2013). We use the OS algorithm from Pﬂamm-Altenburg &
Kroupa (2006)3. In the OS method, any most massive star mass, mmax, of a
given host cluster of mass M follows exactly a theoretical relation, shown by
long-dashed cyan line in Fig. 1.7. However, we modiﬁed the OS so that the
most massive star mass mmax of a given cluster of mass M follows exactly
the empirical relation of Weidner et al. (2013), shown in green solid line in
Figs. 1.6 and 1.7, as it closer represents the observations (shown in Fig. 1.7).
In step 2, we deﬁne a bin around each OS star position. The limits of
the bin are located at half distance in mass space between the star and its
lower and higher mass neighbors. This bin width, wOS, corresponds to the
case when the expansion factor is P = 1.
If we randomly generate stars in each of the bins deﬁned, the mean of
the generated mass in each bin will not necessarily be equal to the mass
of the OS star of the bin. However, this should be the case to ensure that
the mass function of the cluster is conserved. To guarantee this, we slightly
shift the bins, keeping their width wOS constant, so that the means of the
bins coincide with the OS stars. For each bin, this consists in searching the
low-mass a and high-mass b limits of the bin (linked to wOS by wOS = b−a)
3“optimal_sampling”: http://www.astro.uni-bonn.de/en/download/software/
29
0
2
4
6
log10(M/M ⊙)
0
1
2
log10(mmax/M ⊙)
Fig. 1.7.
Sample of the most massive star masses versus the masses of their
host star clusters compiled by Weidner et al. (2013; red points). For comparison,
artiﬁcial star cluster distribution of 1 000 models built with the Reduced Random
Sampling method, with the calibrated mass bin expansion factor P = 6 (black
points) and the correction parameter d = 0.2 (see details in Section 3 on parameter
d), and with addition of errors of the same magnitude as for observations. The
cyan long-dashed line is the theoretical relation derived by Kroupa et al. (2013)
and the green solid line is the third order polynomial ﬁt to the data of Weidner
et al. (2013). The oblique black dashed line is the identity relation between the
mass of the most massive stars and the mass of the host clusters, mmax = M, and
the top black dashed line is the physical upper limit of massive stars, 150 M⊙.
so that we respect the condition4:
mOS = mCDF(a, b)
nCDF(a, b) .
(1.5)
where nCDF is the IMF number Cumulative Distribution Function (shown
in ﬁrst row of Fig. 1.6) and mCDF is the mass Cumulative Distribution
Function. Here we derive them.
We use the Kroupa (2001) IMF (shown in Fig. 1.6) that was deﬁned in
4Following Kroupa (2002). For example, the mean mass of the whole range of mass, [0.01,150]
M⊙of the Kroupa IMF, is 0.38 M⊙(see Table 2 of Kroupa 2002)
30
Eq. 1.2. The nCDF and mCDF are then deﬁned as:
nCDF(mlow, m) =
∫m
mlow
ϕ(m′)dm′ ,
(1.6)
and
mCDF(mlow, m) =
∫m
mlow
m′ϕ(m′)dm′ .
(1.7)
The analytical expressions of nCDF and mCDF are:
nCDF(mlow, m) =
i−1
∑
j=0
kCj
1 −αj
[m1−αj
j+1 −m1−αj
j
] +
kCi
1 −αi
[m1−αi −m1−αi
i
] ,
(1.8)
and
mCDF(mlow, m) =
i−1
∑
j=0
kCj
2 −αj
[m2−αj
j+1 −m2−αj
j
] +
kCi
2 −αi
[m2−αi −m2−αi
i
] ,
(1.9)
where i is deﬁned by m ∈[mi, mi+1] in Eq. 1.2.
As a and b are related by wOS = b −a, Eq. 1.5 is solved for each bin.
Thus, the mass generated in the bin is on average the same as the OS mass
in that bin.
In step 3, the bins of all stars are expanded by multiplying their widths
by an expansion factor, w = P · wOS. Then each star is resampled in its in-
dividual bin. We could see the resampling as the application of the RS used
in, e.g., Santos & Frogel (1997), but restricted to the bins deﬁned around
each OS star position. The mass bins can be expanded for a transition
toward RS (P →∞) or shrinked for a transition toward OS (P →0).
Fig. 1.8 shows the optimally sampled massive stars (gray vertical lines) of
a log10(M/M⊙) = 4 star cluster, and the resampling bins for a few of them
(the colored rectangles), for diﬀerent expansion factor P values. When the
bins are expanded too much, they can exceed the high-mass limit, 150 M⊙.
To avoid this, we group stars belonging to such bins and resample them
within a common bin. In Fig. 1.8 (c), the black bin is a common bin for the
red, blue, and green stars of panels (a) and (b). The high-mass limit of the
common bin is ﬁxed to b = 150 M⊙, and the low-mass limit a is found by
31
a)
P =1
b)
P =5
1.4
1.6
1.8
2.0
2.2
log10(m/M ⊙)
c)
P =15
Fig. 1.8. Masses of the Optimal Sampling stars (gray vertical lines) are shown
for the 1st, 2nd, 3rd, 4th, and 15th most massive stars, respectively from right to
left in colored vertical dashed lines. The associated resampling bins are shown
for several expansion factors: P = 1 (a), 5 (b), and 15 (c). In the case of large
enough expansion factor (c), the resampling bins of the three most massive stars
(red, blue, and green) are grouped in a common bin (shown in black), in which
they will be resampled. The mean mass of the bin is the mean of the OS masses
of the three stars, shown in black thick vertical dashed line. The thin vertical
dashed line shows the high-mass limit, 150 M⊙.
requiring that the mean mass of the common bin equals to the mean mass
of the OS stars grouped into the common bin:
mOS1 + mOS2 + ... + mOSn
n
= mCDF(a, 150)
nCDF(a, 150) ,
(1.10)
where n is the number of grouped stars, e.g., n = 3 in Fig. 1.8(c).
In a similar way, for low-mass stars close to the low-mass limit with
a = 0.01 M⊙, a common bin is also deﬁned by searching for the high-mass
32
limit b.
When generating stars with the sampling algorithm described until here
with bin widths deﬁned as w = P · wOS, we observe a problem in the mmax
vs M relation, displayed in the ﬁrst column of panels in Fig. 1.9. Indeed
for several expansion factors (see cases P = 4, 6), stars in low-mass clusters
(log10(M/M⊙) ∼2.5) almost reach the physical stellar mass limit, while it
is not yet the case for more massive clusters. The reason is that when we
sample the stellar masses with the Optimal Sampling, a low-mass cluster
contains less stars than a massive cluster. Thus the stars of the low-mass
cluster are more distant in the mass space, creating larger bins around them.
For the expansion factors P = 4 and 6, we see that this can create more
massive stars in the low-mass clusters than in the more massive ones, which
is unlikely to be true, considering the Weidner et al. (2013) observations
(see red dots in Fig. 1.7).
We applied a correction as a dependence of the bin width on the mass
of the cluster:
w(M) = P · wOS ·
(
M
103M⊙
)d
.
(1.11)
As emphasized in Fig. 1.9, the choice of the power-law index, d, is guided
by the fact that for d = 0 (see ﬁrst column of panels), the eﬀect is present,
and for high power-law index (d = 0.4, see last column of panels), the mmax
scatter present in massive clusters dominates too much, while it is reduced
in low-mass clusters.
1.3.3
Calibration of the Reduced Random Sampling
To calibrate the best value of the parameters (P, d), we compare the ob-
servational data of Weidner et al. (2013) with the models built with the
Reduced Random Sampling method (see Fig. 1.7). We note that the error
bars of cluster mass and most massive star mass provided by Weidner et
al. (2013) are not statistical quantities but are just lower and higher pos-
sible limits. They derived the masses of the most massive stars using their
spectral classes and assumed an error range as 1/2 of the spectral subclass.
For the masses of the clusters, they have extrapolated them from the visible
stars of the clusters using the IMF (Kroupa 2001). The upper mass limit
was derived assuming that all stars could be unresolved binaries and for
33
1
2
3
4
5
0
1
2
log10(mmax/M ⊙)
d =0
1
2
3
4
5
d =0.2
1
2
3
4
5
P =2
d =0.4
1
2
3
4
5
0
1
2
log10(mmax/M ⊙)
1
2
3
4
5 1
2
3
4
5
P =4
1
2
3
4
5
0
1
2
log10(mmax/M ⊙)
1
2
3
4
5 1
2
3
4
5
P =6
1
2
3
4
5
log10(M/M ⊙)
0
1
2
log10(mmax/M ⊙)
1
2
3
4
5
log10(M/M ⊙)
1
2
3
4
5
log10(M/M ⊙)
P =8
Fig. 1.9.
Dependence of the stochasticity aﬀecting the most massive stars of
star clusters on the d power-law index (indicated on the top of panels) and on the
expansion factor, P, indicated on the right of panels. The ﬁrst column of panels
describes the sampling when no correction is taken into account, d = 0, while the
central and right columns show the sampling generated with a growing correction.
Each panel contains 1 000 cluster models.
the lower limit that half of the stars are misidentiﬁed as cluster members,
foreground or background objects.
We need a statistical description of the uncertainty to introduce it into
the cluster models, and assume that it can be described by a Gaussian
distribution with a sigma taken as 1/3 of the Weidner et al. (2013) error
bars, meaning that these error range limits contain 99% of the measures.
We built several model distributions having diﬀerent (P, d) parameters
and we added errors of the same sigma as deﬁned above. To compare these
distributions to the Weidner et al. (2013) data, we subdivide the model
distributions and the observations in 10 groups according to the cluster
mass between log10(M/M⊙) = 1 and log10(M/M⊙) = 4. In each group i
34
0.01
0.02
0.03
0.02
0.04
0.03
0.05
0.0
0.1
0.2
0.3
0.4
0
5
10
15
20
25
30
P
d
Fig. 1.10. Contour plot
of the likelihood L for the
determination of the best
(P, d) parameters combi-
nation, tested for diﬀerent
model distributions. The
likelihood map is normal-
ized so that the sum of
all models likelihoods is 1.
The best combination is
found at P = 6 and d =
0.2.
we derive the likelihood li between the histogram of the models minus OS
relation and the histogram of the observations minus OS relation. Then a
total likelihood L is derived as a product of the likelihoods li of each group.
The result is presented in Fig. 1.10, where the minimum is found in P = 6,
d = 0.2.
We adopted these parameter values for the distribution shown in Fig. 1.7,
compared to the Weidner et al. (2013) observations.
The few deviating
observations do not inﬂuence signiﬁcantly the selection of the best expansion
factor, as we got the same values of P = 6 and d = 0.2 when we neglected
them. Note that Weidner et al. (2013) indicate that the error ranges do
not take into account other sources of errors like variable extinction, stellar
variability, star loss due to gas expulsion and dynamical interactions. Hence,
it is likely that the true expansion factor P could be smaller than the one
found here, which therefore should be regarded as an upper limit.
The
increase of data and the reﬁnement of errors in Weidner et al. (2013) sample
would help to constrain more accurately the values of the parameters (P, d).
1.3.4
Summary: the Reduced Random Sampling
In this Section, we presented a new sampling method of stellar masses in
clusters, the Reduced Random Sampling, which allows a continuous tran-
sition between the Optimal Sampling and the Random Sampling, already
widely used in unresolved cluster studies. Then, using the catalog of young
35
star clusters from Weidner et al. (2013), we constrained the parameters con-
trolling the level of stochasticity in artiﬁcial clusters. In the following of this
thesis, the sampling scheme used to build stochastic models will remain the
Random Sampling method presented in Section 1.2. The Reduced Random
Sampling presented in this Section is a reﬁnement that still demands to be
conﬁrmed with additional observations in the following years.
1.4
Model grid for age, mass, extinction, and
metallicity
To derive the physical parameters of unresolved star clusters, we computed
a large 4–dimensional grid of discrete cluster models for the age, mass,
extinction, and metallicity, randomly sampling the stellar mass according
to the initial mass function (IMF, Kroupa 2001) following the method based
on Santos & Frogel (1997), described in Section 1.2.
Each node of the
grid contains 1 000 star cluster models. The star luminosities are derived
from stellar isochrones of the selected age and metallicity of the cluster
models. We used the PADOVA isochrones5 from Marigo et al. (2008) with
the corrections of Girardi et al. (2010) for the TP-AGB phases. The grid
was built according to the following nodes: from log10(t/yr) = 6.6 to 10.1
in steps of 0.05, from log10(M/M⊙) = 2 to 7 in steps of 0.05, and for 13
metallicities: from [M/H] = 0.2 to −2.2. This gives a grid of 71 values
of age, 101 values of mass, with 1 000 models per node, hence ∼7 × 106
models for each metallicity. To limit the number of models that need to be
stored in computer’s memory, extinction was computed when the observed
cluster is compared with the grid of models. It ranges from E(B −V ) = 0
to 1 in steps of 0.01, therefore 101 values for the extinction.
We used
the Milky Way standard extinction law from Cardelli et al. (1989) for star
clusters situated in M31, believed to have a similar extinction law as the
Milky Way, or LMC extinction law of Gordon et al. (2003) for star clusters
situated in M33, believed to have a similar extinction law as the LMC.
Fig. 1.11 shows the grid built for diﬀerent metallicities, and illustrates
the eﬀect of the mass and metallicity on the dispersion of integrated U −B
5PADOVA isochrones from “CMD 2.6”: http://stev.oapd.inaf.it/cmd
36
Fig. 1.11. Grids of the stochastic star cluster models. The grids are computed for
the masses log10(M/M⊙) = 3 (ﬁrst column), 4 (second column), 5 (third column),
and all masses in the range log10(M/M⊙) = [2, 7], to show the full dispersion of
the models. The top row is for solar metallicity, [M/H] = 0, the central row for
LMC metallicity, [M/H] = −0.4, and the bottom row for very low metallicity,
[M/H] = −2.
and B−V colors of clusters. The three ﬁrst columns show the grid for a ﬁxed
mass, increasing from left (log10(M/M⊙) = 3) to right (log10(M/M⊙) = 5,
similar to the SSP models). The last column shows the grid for all masses
together. The metallicities of the model grid shown are [M/H] = 0, -0.4
and -2 from top row to bottom row of panels. As shown in Fig. 1.1 by use
of SSP or in Fig. 1.5 for a few nodes of grid, we see that the sequence does
not go red in U −B and B −V for the metal-poor model grid (lower row of
panels), contrarily to the case of more metal-rich grid (upper row of panels).
With the construction of this age-mass-extinction-metallicity grid of
stochastic star cluster models, one can derive consistently the star cluster
parameters, as presented in the next chapter.
37
38
Chapter 2
Deriving the Cluster Parameters
2.1
The
method
of
star
cluster
parameters
derivation
The main idea of the method for deriving the physical parameters (age,
mass, extinction, and metallicity) of a given observed star cluster with avail-
able broad-band photometry is to compare its magnitudes with those of a
4–dimensional grid of models for every value of the four physical parame-
ters. Each node of the model grid described in the previous section contains
a large series of models of the same age, mass, extinction, and metallicity
to represent stochastic variations in photometry.
Here is the ﬁrst method of derivation of the star cluster parameters.
A 4–dimensional grid of cluster models is built for every value of the four
physical parameters, log10(t/yr), log10(M/M⊙), E(B −V ), [M/H] ; for sim-
plicity Fig. 2.1 (a) shows only a grid for age and mass. For the description
of the sampling method to generate cluster models, see Section 1.2, and
for the description of the grid, see Section 1.4. Each node of the grid con-
tains 1 000 models of the same age, mass, extinction, and metallicity. They
populate the photometric parameter space (absolute UBV RI magnitudes).
Figure 2.1 (b) shows MU and MB with only 100 models per node without
extinction (the used model grid is much more continuous in photometric
parameter space).
When the observations are considered in Fig. 2.1 (c), along with their er-
ror bars (σ; hereafter we use σ = 0.05 mag for all the passbands of artiﬁcial
and real cluster samples studied in Chapter 3 unless speciﬁed otherwise),
which in general can be diﬀerent for every magnitude, all the models sit-
uated within 3–σ from the observed magnitudes are selected. Fig. 2.1 (d)
shows the nodes to which the selected models are associated. Other nodes
do not play any role in the derivation of parameters. Finally, the distri-
39
physical
photometric
Space of parameters
a)
d)
b)
c)
log   ( / yr)
   t
10
2
4
6
0
0.1
0.2
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
log   (M/ M  )
10
log   ( / yr)
   t
10
log   (M/ M  )
10
log   ( / yr)
   t
10
log   (M/ M  )
10
Fig.
2.1.
Scheme
of the method for deriv-
ing physical parameters of
star cluster.
Panel (a)
shows the grid of models
(only age and mass are
displayed;
same for ex-
tinction and metallicity).
These models are repre-
sented in the photometric
space (only MU and MB
are shown) displayed in
panel (b) (only 100 mo-
dels per node without ex-
tinction are shown).
In
panel (c) all the models
situated within 3–σ (cir-
cle) from the observed ab-
solute magnitudes are se-
lected.
Panel (d) shows
the nodes associated with
these models.
The 1-
dimensional age and mass
distributions
of
the
se-
lected
models
are
dis-
played as normalized his-
tograms in panels (e) and
(f),
used
to
determine
most probable values, in-
dicated by solid vertical
lines; conﬁdence intervals
are indicated by dashed
lines.
butions of age and mass, displayed in Figs. 2.1 (e, f), are derived from the
selected models, as for the extinction and metallicity, which are not shown
in the ﬁgure.
For the selected models (Fig. 2.1 (c), red circle) we apply weights as
follows: for the models located within 1–σ from the observed magnitude
a weight of 0.68 is assigned, for the ones between 1–σ and 2–σ a weight
of 0.28, and for the ones between 2–σ and 3–σ a weight of 0.04.
The
probability density distributions displayed in Figs. 2.1 (e, f) are derived by
normalizing the total area of each histogram to 1. The solution is taken as
the maximum of these 1–dimensional distributions. We compute conﬁdence
40
intervals (error bars) by excluding the ﬁrst and the last 16% of the area in
histograms, following the method of “central interval” presented in § 2.5.1
of Andrae (2010).
The second method is a mathematical generalization of the ﬁrst method.
In a similar way as Fouesneau & Lançon (2010) and Fouesneau et al. (2014),
we evaluated the likelihood of each node of the grid to represent the mag-
nitudes of a given observed cluster. For each node, we ﬁrst computed the
likelihood of each model from the node by
Lmodel =
F
∏
f=1
1
√
2π σf
exp
[
−
(
magf,obs −magf,model
)2
2 σ2
f
]
,
(2.1)
where f stands for one particular passband, magf for the observed and
model magnitudes in that passband, and F for the total number of pass-
bands, for example 5 for the UBV RI photometric system. Then the likeli-
hood of the node of age t, mass M, extinction E(B −V ), and metallicity
[M/H] is the sum of the likelihoods of its models,
Lnode (t, M, E(B −V ), [M/H]) =
N
∑
n=1
Lmodel, n ,
(2.2)
where N is the total number of models contained in the node. The ob-
served star cluster is then classiﬁed with the parameters of the node, which
maximizes Lnode among all nodes of the grid.
Note that this procedure could be also applied by using colors (e.g.
U −B, u∗−g′, or other passbands combinations) in place of individual
magnitudes, in the variable magf of Eq. 2.1. In this thesis, we will use the
method applied on magnitudes unless explicitly expressed otherwise.
2.2
Improvement on the derivation of parame-
ters
This section presents a third method of derivation of star cluster parameters
and is the object of a paper in preparation (in which the method will be
released for public use). This method is an analytical generalization of the
41
second method presented in 2.1.
Cerviño & Luridiana (2006) made an unfruitful attempt to ﬁnd a com-
plete analytical method of derivation of star cluster physical parameters
when their colors are integrated, which takes stochasticity into account.
Present-day methods of derivation of star cluster parameters, which take
the stochasticity problem into account, are based on a large age-mass-
extinction (and metallicity, in our case) grids of star cluster models. For
each node of the grid, a large collection of models is built to reproduce the
stochastic distribution of colors (or magnitudes) of the clusters for these
parameters. For example, Fouesneau & Lançon (2010), Popescu & Hanson
(2010), and Popescu et al. (2012) take several thousands models per node,
what means that an entire grid may contain several millions of models (up
to one hundred of millions in Popescu et al. 2012). This makes the search
of the solution very long for the derivation of clusters parameters.
In this Section, we developed a method which aims to solve this prob-
lem. The idea is to replace the large collection of models for each node by
a multivariate Gaussian Mixture Model (GMM), which would analytically
describe the grid. Each node of the grid, containing 1 000 models (or more)
can be approximated by a collection of multivariate (i.e. multidimensional,
for example in the UBV RI passband space) Gaussian functions fi with
corresponding weights ϕi. With a high enough number of such Gaussian
functions, virtually all shapes in the photometric space could be eﬃciently
reproduced by use of the Expectation-Maximization algorithm (EM, Demp-
ster et al. 1977).
Mathematically, each node can be described as a probability distribution
function (PDF), which is the sum of the Gaussians components:
Pnode(⃗x|t, M, EB−V , [M/H]) =
∑
i
ϕi(⃗x)fi(⃗x|⃗µi, ⃗Σi)
(2.3)
where ⃗x is a vector containing the diﬀerent magnitudes of the observed
cluster, ⃗µ is the vector containing the diﬀerent magnitudes of the mean of
the component i, Σi is the covariance matrix which shapes each of the i
Gaussian components fi, and ϕi is the weight of each Gaussian component
fi. The Gaussian function fi(⃗x|⃗µi, ⃗Σi) is the PDF of the component i, which
42
can be written as:
fi(⃗x|⃗µi, ⃗Σi) =
1
(2π)D/2 ⃗
|Σi|
1/2 exp
(
−1
2(⃗x −⃗µi)T ⃗Σi
−1(⃗x −⃗µi)
)
,
(2.4)
where D is the number of dimensions in the photometric space, for example
D = 5 for the UBV RI space.
The weighted sum of the functions fi(⃗x|⃗µi, ⃗Σi) is the analytical general-
ization of the discrete PDF of a given node (see Eqs. 2.1 and 2.2). Hence,
to derive the parameters of an observed cluster, we have to maximize the
likelihood of the node, given in Eqs. 2.3 and 2.4, i.e., to search the node
that maximizes the quantity Pnode(⃗x|t, M, EB−V , [M/H]).
We used the GMM algorithm from scikit-learn1 (Pedregosa et al. 2011)
and found that the composition of 10 Gaussian models can eﬃciently repro-
duce the stochasticity for any composition of parameters, hence any node of
the grid. Fig. 2.2 illustrates the comparison of such GMMs and correspond-
ing nodes of discrete Monte-Carlo models. The blue circles in top panels of
Fig. 2.2 are 1 000 star cluster models generated by random sampling, con-
stituting one node from the discrete grid, with age log10(t/yr) = 7, mass
log10(M/M⊙) = 3, and metallicity [M/H] = 0. The density plots in bottom
panels are the associated GMM models for this node. This GMM models
can be seen as a PDF and hence discrete samples can be generated from
them, such as the green circles shown for comparison to the real cluster
models in top panels of the ﬁgure.
Fig. 2.3 shows the same comparison
for an other node of the grid, older (log10(t/yr) = 8) and more massive
(log10(M/M⊙) = 4).
Using this approach allows to speed up the derivation of star cluster
parameters by a factor 10. Also, a very interesting advantage of this GMM
method is that it can be based on a grid of models composed of 1 000
models per node, or 10 000 models per node or even more; it will be the
same room in memory, as nodes are compressed in a few numbers describing
the analytical Gaussian mixture.
To summarize, the GMM approach:
1http://scikit-learn.org/stable/modules/mixture.html
43
1
0
U−B
8
7
6
U
8
7
6
5
V
0
1
2
V−I
1
0
U−B
8
7
6
5
B
8
7
6
U
10
9
8
7
6
5
I
8
7
6
5
V
Fig. 2.2. Top panels: comparison of the 1 000 models created by Random Sam-
pling (hence a node of the grid, blue circles) vs the models resampled from the
Gaussian Mixture Models (green circles). Here the node from the grid has age
log10(t/yr) = 7, mass log10(M/M⊙) = 3, and metallicity [M/H] = 0. Bottom
panels: density plot of the GMM approximation of the node. This shows that
GMM models can reproduce any kind of nodes.
0.38
0.34
0.30
0.26
U−B
7.4
7.3
U
7.3
7.2
7.1
7.0
V
0.2
0.4
0.6
0.8
V−I
0.34
0.30
0.26
U−B
7.10
7.05
7.00
B
7.4
7.3
U
8.0
7.5
7.0
I
7.3
7.2
7.1
7.0
V
Fig. 2.3. Same as Fig. 2.2 but for a grid node with age log10(t/yr) = 8, mass
log10(M/M⊙) = 4, and metallicity [M/H] = 0.
44
• allows to describe a grid of node eﬃciently, by contracting it to a given
number of GMM parameters,
• allows an analytical derivation of the star cluster physical parameters,
avoiding the long process of derivation of likelihood of each of the 1 000
models in each node in the approach presented in Section 2.1 .
2.3
Test of the method with an artiﬁcial cluster
sample
We simulated artiﬁcial star cluster samples with known age, mass, extinc-
tion, and metallicity and used them as input clusters to evaluate the ability
of our method to derive physical parameters. The artiﬁcial cluster samples
consist of 10 000 clusters with ages uniformly distributed in the log10(t/yr)
range [6.6, 10.1]. To simulate the mass of input clusters, we used a power-
law cluster mass function with index −2 in the range log10(M/M⊙) = [2.7,
4.3], so as to have more low-mass clusters in the sample.
We have two
artiﬁcial samples: one without extinction and the other with E(B −V )
(uniformly distributed) in the range [0, 1] using the Milky Way standard
extinction law from Cardelli et al. (1989). In this Section, the metallicity
is ﬁxed to [M/H] = −0.4.
The eﬀects of metallicity will be studied in
Sections 2.4, 2.5, and 2.6.
Figure 2.4 displays the results for artiﬁcial cluster sample built without
extinction.
Panels (a) and (b) show the results of the age and mass of
the artiﬁcial cluster sample without introducing photometric observation
errors. Panels (c) and (d) show the case with Gaussian photometric errors
of 0.05 mag, randomly added to each magnitude of the sample clusters.
The introduction of photometric errors results in broadening around the
one-to-one line.
In Fig. 2.4 (b), the asymmetry observed in the mass derivation slightly
favors high masses. This is because, in the grid of star cluster models, the
nodes of models with higher mass have magnitudes that are less dispersed
than the nodes with lower mass models, as a consequence of stochasticity
(as it has been shown in Fig. 1.5). Thus, when the models of two nodes of
diﬀerent masses are located in the UBV RI “sphere” around the observation
45
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
5
4
3
5
4
3
5
4
3
a)
c)
b)
d)
Number of models per bin
3
10
30
100
log   (M/ M  ) true
10
log   (M/ M  ) derived
10
log   ( / yr) true
   t
10
log   ( / yr) derived
   t
10
Fig. 2.4.
Derived pa-
rameters of 10 000 artiﬁ-
cial clusters without ex-
tinction.
Panels (a) and
(b) show age and mass
for a sample without pho-
tometric errors; (c) and
(d)
for
a
sample
with
Gaussian photometric er-
rors of 0.05 mag. Panel (b)
also shows the means and
standard deviations (cir-
cles with error bars) of
the derived mass distribu-
tions for clusters with true
mass log10(M/M⊙) = 3,
3.5 and 4.
The density
scale is logarithmic.
shown in Fig. 2.1 (c), the more massive node, with less dispersed models,
will dominate. To balance out the eﬀect, a cluster mass function could be
used to decrease the importance of the nodes of massive cluster models.
Although Fig. 2.4 (b) shows asymmetry, the means and standard deviations
given at log10(M/M⊙) = 3, 3.5, and 4 indicate that this phenomenon is
slight.
Figure 2.5 gives the results of artiﬁcial clusters in the case of extinction
aﬀecting the photometry of clusters.
Panels (a), (b), and (c) show the
age, mass and extinction derived when there are no photometric errors,
and panels (d), (e), and (f) when there are Gaussian photometric errors
of 0.05 mag included. In Fig. 2.5 (d), in the case of photometric errors and
extinction, we observe that the broadening around the one-to-one relation
increases, especially for log10(t/yr) ≳8, which is associated with broadening
in the extinction (panel f), what is a sign of the age-extinction degeneracy.
It creates two streaks above and below the one-to-one relation in the range
of 8 ≲log10(t/yr) ≲9.5 that were already perceptible in the case without
photometric errors in Fig. 2.5 (a). However, including of photometric errors
does not signiﬁcantly aﬀect the derivation of mass (panels b and e). We note
that a gap in derived ages at log10(t/yr) = 9.15 is a feature of isochrone due
46
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
log   ( / yr) derived
   t
10
log   ( / yr) true
   t
10
log   (M/ M  ) true
10
log   (M/ M  ) derived
10
Fig. 2.5.
Derived parameters of 10 000 artiﬁcial clusters with extinction randomly
chosen in the range of E(B −V ) = [0, 1]. Panels (a), (b) and (c) show age, mass, and
extinction for a sample without photometric errors; (d), (e), and (f) for a sample with
Gaussian photometric errors of 0.05 mag.
to the increase in the production rate of AGB stars, which was discussed in
Girardi & Bertelli (1998).
These degeneracy streaks have ﬁrst been reported by Fouesneau &
Lançon (2010). The degeneracy streak above the one-to-one line seen in
Fig. 2.5 (d) concerns clusters that are young and that possess intrinsically
high extinction, but are derived by the method as older and having lower
extinction. Conversely, the streak of clusters below the one-to-one relation
involves objects that are derived as younger and that have higher derived
extinction than they do in reality. These features are important to keep in
mind when deriving the physical parameters of unresolved star clusters.
2.3.1
Is it possible to reduce the age-extinction degener-
acy?
The upper and lower streaks in Fig. 2.5 (d) suggest that if a wide extinction
range is allowed in a simulated sample, then there are possibilities that a
cluster mimics an older one with lower extinction, or inversely a younger
one with higher extinction. If the true extinction range of the cluster popu-
lation is narrow, then we could restrict the search for the extinction within
47
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
5
4
3
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
10
9
8
7
10
9
8
7
100
30
10
3
Number of models per bin
log   ( / yr) true
   t
10
log   (M/ M  ) true
10
log   ( / yr) derived
   t
10
log   (M/ M  ) derived
10
Fig. 2.6. Derived parameters of 10 000 artiﬁcial clusters with true extinction randomly
chosen in the range of E(B−V ) = [0, 0.5] with Gaussian photometric errors of 0.05 mag.
Panels (a), (b), and (c) show age, mass and extinction when a sample is studied using
a grid of models with an allowed extinction in the range of [0, 1]; (d), (e), and (f) show
the results for the same cluster sample studied with a narrower allowed extinction in
the range of [0, 0.5]. Panels (c) and (f) are denser than in Fig. 2.5, because the same
number of clusters are located on a smaller range of extinction. A square indicated in
panels (a) and (d) is used to quantify the degeneracy eﬀect.
a narrow range in the model grid, resulting in decrease of age-extinction
degeneracy.
In Fig. 2.6 we show results of the tests for a sample of 10 000 artiﬁcial
clusters with true extinction from a range of E(B −V ) = [0, 0.5] and with
Gaussian photometric errors of 0.05 mag randomly added to each magnitude
of the sample clusters. This cluster sample was studied twice, with diﬀerent
allowed extinction ranges in the model grid.
In the ﬁrst test, the extinction of the model grid was allowed to vary in
a wide range, E(B −V ) = [0, 1], shown in Fig. 2.6 (a, b, c). If a cluster
has a true extinction of 0.5 mag, then the maximum underestimation of its
extinction can be from 0 to 0.5 mag. But if a cluster has true extinction
of 0, the maximum overestimation of its extinction could range from 0 to
1 mag. This explains why the lower streak (i.e. clusters with overestimated
extinction) is more extended than the upper one in panel (a).
In the second test, the allowed extinction range of the model grid was
48
reduced to a range of [0, 0.5]; Fig. 2.6 (d, e, f).
The constraint on the
extinction range resulted in a reduction of the lower degeneracy streak,
seen in Fig. 2.6 (d), which is less developed than in Fig. 2.6 (a). From the
comparison of Figs. 2.6 (b) and (e), we see that the mass is less aﬀected by
the degeneracy. We note that only the lower streak is modiﬁed, since only
the higher limit of the allowed extinction range was changed from 1.0 to
0.5 mag. The upper streak is not modiﬁed, because the lower limit of the
allowed extinction range was not changed.
To quantify the reduction of the lower degeneracy streak due to reduction
of the extinction range, all the models situated in the square shown in
Figs. 2.6 (a) and (d) were counted. There are ∼480 clusters in that region
for the wide extinction range (panel a) and only ∼110 for the low extinction
range (panel d). The reduction of the extinction range from E(B −V ) =
[0, 1] to [0, 0.5] thus decreases more than four times the strength of the
degeneracy streak.
We conclude that to reduce the degeneracy streaks seen in Fig. 2.5 (d),
we should make a reasonable assumption on the extent of the possible ex-
tinction range within the galaxy hosting the studied cluster population.
2.4
Metallicity eﬀects: one–metallicity vs one–
metallicity
To characterize the sensitivity of the accuracy of the method presented
in Section 2.1 on the metallicity parameter, we built samples of 10 000
stochastic artiﬁcial clusters with a uniform random distribution in the age
range log10(t/yr) = [6.6, 10.1] and a uniform random distribution in the
extinction range E(B−V ) = [0, 1], with the mass ﬁxed to log10(M/M⊙) = 4
and for 3 metallicities, [M/H] = 0, −0.6, and −2. These artiﬁcial clusters
were built with photometry available in the optical (UBV RI), near-infrared
(JHK), and ultraviolet (GALEX) passbands.
2.4.1
Parameter derivation for artiﬁcial clusters in UBV RI
In this ﬁrst test, we show the results of deriving age, mass, and extinction
using UBV RI passbands alone. Photometric errors were included in the
UBV RI photometry of artiﬁcial clusters by adding Gaussian errors of σ =
49
7
8
9
10
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
7
8
9
10
log10(t=yr) derived
¡0:6
7
8
9
10
7
8
9
10
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
a)
1
3
5
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
1
3
5
N
¡0:6
3
4
5
1
3
5
3
4
5
log10(M=M ¯) derived
3
4
5
¡2:0
b)
−0.8
−0.4
0.0
0.4
0.8
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡E(B¡V) true
¡0:6
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
c)
Fig. 2.7.
Results of the tests for
three samples of artiﬁcial clusters using
UBV RI photometry. The true metalli-
city of the models is speciﬁed at the right
of each block and the metallicity of the
grid used to classify the clusters is speci-
ﬁed at the top. Blocks of panels show the
derived (a) age, (b) mass (the total area
of each histogram is normalized to one),
and (c) extinction.
In each block, the
main diagonal panels are those where the
true metallicity and the metallicity of the
grid are the same, [M/H]true = [M/H]used.
0.05 mag to each magnitude.
In Fig. 2.7, the results show that the parameters are derived best when
the metallicity used to classify clusters is the same as the true metallicity;
see results in the main diagonal panels of the three panel blocks of Fig. 2.7.
In the main diagonal panels of the age parameter (Fig. 2.7 a), the streaks
that develop perpendicularly up and down compared to the one-to-one black
dashed line are caused by the age-extinction degeneracy. Old clusters with
low intrinsic extinction can be mistakenly classiﬁed as younger clusters with
higher extinction, and vice versa (see Fouesneau & Lançon 2010, as well
as Section 2.3 for more details on the age-extinction degeneracy).
Fig. 2.8 shows the diﬀerence of extinction (derived −true) vs the dif-
ference of age (derived −true) for clusters with true metallicity that were
analyzed with model grids of the same metallicity, like in the main diago-
50
−0.5
0.0
0.5
[M=H] =0
¡0:6
UBVRI
¡2
−0.5
0.0
0.5
E(B¡V) derived ¡ true
UBVRIJHK
−2
0
2
−0.5
0.0
0.5
−2
0
2
log10(t=yr) derived ¡ true
−2
0
2
GALEX +UBVRI
Fig. 2.8.
Diﬀerence of
the derived and the true
extinction versus the dif-
ference of the derived
and the true age for
the sample of 10 000 ar-
tiﬁcial clusters.
Clus-
ters have been classiﬁed
according to their true
metallicity ([M/H]true =
[M/H]used), which is in-
dicated at the top of
panels,
and with
dif-
ferent photometric sys-
tems, indicated at the
right.
nal panels of Fig. 2.7. The top row of panels in Fig. 2.8 shows the results
obtained with the UBV RI photometric system. The extinction and age
derivations are tightly related: an underestimation of the age correlates
with an overestimation of the extinction, and an overestimation of the age
correlates with an underestimation of the extinction. With decreasing me-
tallicity, we note a slight change of the degeneracy correlation and concen-
tration.
The panels above and below the main diagonal panels of Fig. 2.7 show
the results where the metallicity of the grid is diﬀerent from the true one,
therefore additional biases appear. For the age parameter (panels block a)
we observe a reinforcement of the left part of the age-extinction degeneracy
streak when the grid metallicity is lower than the true metallicity (panels
above the main diagonal panels) and a reenforcement of the right part of the
streak when grid metallicity is higher than true metallicity (panels below
the main diagonal panels).
Essentially, when the grid metallicity is higher than the true metallicity
(panels below the main diagonal panels), the underestimation of the ages of
old clusters can be understood because, for the same age, mass, and extinc-
tion, low-metallicity clusters are generally brighter and bluer than high-
51
7
8
9
10
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
7
8
9
10
log10(t=yr) derived
¡0:6
7
8
9
10
7
8
9
10
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
a)
1
3
5
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
1
3
5
N
¡0:6
3
4
5
1
3
5
3
4
5
log10(M=M ¯) derived
3
4
5
¡2:0
b)
−0.8
−0.4
0.0
0.4
0.8
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡E(B¡V) true
¡0:6
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
c)
Fig. 2.9.
Same as Fig. 2.7, but for
UBV RI + JHK passbands with σ =
0.05 mag for the photometric Gaussian
errors for each UBV RI passband, and
σ = 0.1 mag for each JHK passband.
metallicity clusters. This is why classifying low-metallicity clusters with
a higher-metallicity grid will interpret this brightness as that of younger
clusters. Moreover, the degeneracy exists not only between the age and
metallicity: the clusters are perceived to be much younger than they are,
but also less massive (Fig. 2.7 b). The extinction (Fig. 2.7 c) is also aﬀected,
so that the degeneracies are strongly multidimensional. The reverse eﬀects
are also true for the upper main diagonal panels, when the grid metallicity
is lower than the true one. Out of main diagonal results show how much
derived parameters would be biased when trying to derive their values for
unresolved clusters using an incorrect metallicity for the model grid.
52
2.4.2
Addition of near-infrared passbands: UBV RI + JHK
By using simple stellar population models (SSP), Bridžius et al. (2008)
(see also Anders et al. 2004) showed that adding near-infrared information
(JHK photometric bands) to optical UBV RI passbands could help to sig-
niﬁcantly decrease the age-extinction degeneracy. We performed the same
tests with stochastic clusters with additional JHK passbands.
In each
JHK passband, we added Gaussian photometric errors of σ = 0.1 mag
to mimic the larger photometric uncertainties present in these passbands.
We kept σ = 0.05 mag for the Gaussian photometric errors added to the
UBV RI passbands.
The results are displayed in Fig. 2.9. The main diagonal panels of the age
and extinction parameter blocks (respectively a and c) show that the age-
extinction degeneracy is reduced signiﬁcantly. The streaks perpendicular to
the one-to-one dashed line in the age parameter block (Fig. 2.9 a) are much
less populated than when only UBV RI passbands were used (Fig. 2.7 a).
The decrease of intensity of the age-extinction degeneracy is also visible
in Fig. 2.8 (second row), compared with the case without JHK passbands
(ﬁrst row).
However, out of the main diagonal panels of Fig. 2.9, hence when the grid
metallicity is diﬀerent from the true metallicity of clusters, the strong addi-
tional biases due to metallicity seen in UBV RI-only case are still present,
despite some minor diﬀerences.
2.4.3
Addition
of
ultraviolet
passbands:
GALEX + UBV RI
It is well-known (e.g.,
Kaviraj et al. 2007) that the association of
far-ultraviolet (FUV) and near-ultraviolet (NUV) passbands with optical
UBV RI passbands helps in reducing degeneracies in the derivation of pa-
rameters.
Here we study the samples of 10 000 stochastic artiﬁcial star
clusters with UBV RI photometry, with σ = 0.05 mag for the photometric
Gaussian errors, and GALEX photometry with σ = 0.15 mag for each of
the FUV and NUV passbands.
Fig. 2.10 shows the results for this passband combination, sharply con-
straining the age, mass, and extinction. The age-extinction streaks present
53
7
8
9
10
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
7
8
9
10
log10(t=yr) derived
¡0:6
7
8
9
10
7
8
9
10
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
a)
1
3
5
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
1
3
5
N
¡0:6
3
4
5
1
3
5
3
4
5
log10(M=M ¯) derived
3
4
5
¡2:0
b)
−0.8
−0.4
0.0
0.4
0.8
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡E(B¡V) true
¡0:6
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
c)
Fig. 2.10.
Same as Fig. 2.7, but with
GALEX (FUV and NUV) and UBV RI
passbands with σ = 0.05 mag for the
photometric Gaussian errors for each
UBV RI passband, and σ = 0.15 mag
for each GALEX passband.
in main diagonal panels in previous tests (Fig. 2.7 and 2.9) here vanish en-
tirely. This is also clear in the last row of panels of Fig. 2.8, where the
correlation present in UBV RI and UBV RI + JHK cases fades.
The break of the age-extinction degeneracy brought by ultraviolet data
can be understood in Fig. 2.12. Panel (a) shows the SSPs of the 13 metallic-
ities in optical passbands alone as well as the distributions of 1 000 discrete
cluster models of mass log10(M/M⊙) = 4, of age log10(t/yr) = 7, 7.5, 8, 8.5,
9, 9.5, and 10, for three metallicities: [M/H] = 0, −0.6, and −2. In that
case, for a given SSP of ﬁxed metallicity, the bending of the SSP curve at
intermediary ages and the direction of the reddening vector allow an age-
extinction degeneracy between young and old clusters. This is also true in
terms of discrete model distributions, because the distributions of a given
metallicity follow the SSP line of the corresponding metallicity. Fig. 2.12 (b)
54
shows that this is not anymore the case when ultraviolet data are used, as
the reddening vector now strongly deviates from the SSP direction.
However,
as seen in previous tests,
oﬀsets are also observed in
Fig. 2.10 (a) when the grid metallicity is diﬀerent from the true one (out
of main diagonal panels), but the scatter is much smaller here. As before,
when the metallicity of the grid is higher than the true one (panels below
the main diagonal panels), the age is classiﬁed as younger and the mass as
lower, and the reverse is true when the grid metallicity is lower than the
true one (panels above main diagonal panels).
Note, however, that these results are in practice not useful for clusters
older than a few hundred million years, as the FUV and NUV magnitudes
strongly fade later on (see, e.g., Bianchi 2011). This means that to esti-
mate the parameters of star clusters of close galaxies such as Andromeda
or Triangulum, GALEX data can only be used for young clusters because
for older clusters ultraviolet photometry falls below the detection limit.
2.5
Metallicity eﬀects: one–metallicity vs whole
metallicity range
In this Section we present the derivation of star cluster parameters when
the metallicity of the model grid extends on a wide range. The aims are to
see how much the derivation of the age, mass, and extinction deteriorates
compared to the case where the metallicity is ﬁxed to the correct value, and
also to see if we can derive a reliable estimation of the metallicity parameter
itself.
It is good to remember that the sensitivity of a photometric system to age
and metallicity parameters can vary strongly, depending on which spectral
area it is situated in. This is presented in Fig. 2.11, where the spectra of SSP
models (built using PEGASE package2, Fioc & Rocca-Volmerange 1999) are
displayed for three metallicities ([M/H] = 0.2, -0.4, and -1.8) and for seven
ages (10 Myr, 50 Myr, 100 Myr, 500 Myr, 1 Gyr, 5 Gyr, and 10 Gyr), and
compared to the passbands of the diﬀerent photometric systems used in
this thesis: GALEX, UBV RI, 2MASS (second panel), and WFC3 (third
2http://www2.iap.fr/pegase/
55
5
10
15
20
25
30
log10(Flux) + constant
λ [µm]
0.2
0.6
1.0
T(λ)
5000
10000
15000
20000
λ [angstrom]
0.2
0.6
1.0
T(λ)
Fig. 2.11. Top panel: integrated spectra of SSP models built using PEGASE
code (Fioc & Rocca-Volmerange 1999) for three metallicities: [M/H] = 0.2 (red),
[M/H] = −0.4 (green), and [M/H] = −1.8 (blue). The spectra are built for seven
diﬀerent ages, 10 Myr, 50 Myr, 100 Myr, 500 Myr, 1 Gyr, 5 Gyr, and 10 Gyr, from
bottom to top, and shifted vertically not to overlap. Central panel: photometric
passbands shown for GALEX (FUV and NUV, solid line), UBV RI (long-dashed
line), and 2MASS JHK (short-dashed line). Bottom panel: WFC3 photometric
passbands F275W, F336W, F475W, F814W, F110W, and F160W. To guide
the eye, shaded areas trace GALEX (dark shade), UBV RI (medium shade), and
2MASS (light shade) photometric zones in the whole ﬁgure. This ﬁgure is based
on a ﬁgure of Bianchi (2011).
56
Fig. 2.12.
Color vs magnitude diagrams showing the SSP curves of the 13
metallicities used in the model grid, with discrete model distributions of age
log10(t/yr) = 7, 7.5, 8, 8.5, 9, 9.5, and 10 (young models are top left and old
models are bottom right in each panel), for three metallicities: [M/H] = 0 (red),
−0.6 (orange) and −2 (blue). Each distribution contains 1 000 discrete cluster mo-
dels with mass ﬁxed to log10(M/M⊙) = 4, and the SSPs are scaled to the mass of
the clusters. The reddest SSP line indicates the highest metallicity, [M/H] = 0.2,
and the bluest SSP line indicates the lowest metallicity, [M/H] = −2.2. The 1–σ
(σ =0.15 mag for FUV and NUV, and 0.05 mag for U and B passbands) error
bars show the standard deviations of the photometric accuracy. The black arrows
indicate the extinction vector, computed for AV = 1 mag. Panel (a) shows the sit-
uation in optical bands alone, while in panels (b) and (c), ultraviolet information
is present, and the zoom plots show the details at young age.
panel). To guide the eye, the shaded areas emphasize the GALEX, UBV RI,
and 2MASS zones of interest. Several striking features are visible: for a
ﬁxed metallicity, the spectra most vary in the ultraviolet GALEX area, and
thus explains why the GALEX photometric system is a strong indicator
of the age. Also, the spectra of diﬀerent metallicities are most diﬀerent in
the ultraviolet after 100 Myr, and in the infrared below 100 Myr. Although
derived by use of SSP model spectra, these features are good to keep in
mind for interpretation of the results of the artiﬁcial tests.
We study the parameter derivation of three artiﬁcial clusters samples,
each of them with one ﬁxed metallicity ([M/H] = 0, −0.6, and −2), us-
ing a large grid containing cluster models of 13 diﬀerent metallicities (from
[M/H] = 0.2 to [M/H] = −2.2), to determine the ability of the method to de-
rive the cluster age, mass, and extinction when the metallicity is unknown,
with an attempt to also constrain the metallicity itself. First, we apply the
method using only UBV RI photometry, then using UBV RI + JHK pho-
tometry, and, ﬁnally, using GALEX + UBV RI photometry. As previously,
the mass of clusters was ﬁxed to log10(M/M⊙) = 4, and the models were
57
7
8
9
10
7
8
9
10
log10(t=yr) derived
a)
Errors : 0:05 mag (UBVRI)
[M=H]true =0:0
3
4
5
1
3
5
N
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡true
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
75%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) derived
7
8
9
10
log10(t=yr) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
20%
7
8
9
10
¡2:0
3
4
5
7
8
9
10
0.0 -0.6 -1.2 -1.8
45%
7
8
9
10
7
8
9
10
log10(t=yr) derived
b)
Errors : 0:05 mag (UBVRI) 0:10 mag (JHK)
[M=H]true =0:0
3
4
5
1
3
5
N
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡true
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
75%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) derived
7
8
9
10
log10(t=yr) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
35%
7
8
9
10
¡2:0
3
4
5
7
8
9
10
0.0 -0.6 -1.2 -1.8
60%
7
8
9
10
7
8
9
10
log10(t=yr) derived
c) Errors : 0:05 mag (UBVRI); 0:15 mag (GALEX)
[M=H]true =0:0
3
4
5
1
3
5
N
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡true
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
80%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) derived
7
8
9
10
log10(t=yr) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
50%
7
8
9
10
¡2:0
3
4
5
7
8
9
10
0.0 -0.6 -1.2 -1.8
65%
Fig. 2.13.
Age, mass, extinction, and
metallicity derived for samples of 10 000
artiﬁcial clusters and with true mass
log10(M/M⊙) = 4 when the metallicity
is unknown. In each case, the true me-
tallicity is indicated at the top of each
column, and also by the vertical dashed
line in metallicity panels (bottom row
of panels).
In the block of panels (a),
only UBV RI photometry has been used
with σ = 0.05 mag of photometric er-
rors. In block (b) JHK passbands have
been added to UBV RI, with σ = 0.1
mag of photometric errors.
In block
(c) GALEX passbands have been added
to UBV RI, with 0.15 mag of photome-
tric errors. In metallicity panels, regions
are deﬁned around the true metallicities
(shaded area ±2 bins around the true
metallicities). The percentage of clusters
classiﬁed according to metallicity in this
region is indicated.
Mass and metalli-
city histograms are normalized so that
the area below the histogram is 1.
58
7
8
9
10
7
8
9
10
log10(t=yr) derived
a)
Errors : 0:05 mag (UBVRI)
[M=H]true =0:0
3
4
5
1
3
5
N
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
80%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
35%
7
8
9
10
¡2:0
3
4
5
0.0 -0.6 -1.2 -1.8
70%
7
8
9
10
7
8
9
10
log10(t=yr) derived
b)
Errors : 0:05 mag (UBVRI) 0:10 mag (JHK)
[M=H]true =0:0
3
4
5
1
3
5
N
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
75%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
55%
7
8
9
10
¡2:0
3
4
5
0.0 -0.6 -1.2 -1.8
75%
7
8
9
10
7
8
9
10
log10(t=yr) derived
c) Errors : 0:05 mag (UBVRI); 0:15 mag (GALEX)
[M=H]true =0:0
3
4
5
1
3
5
N
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
80%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
55%
7
8
9
10
¡2:0
3
4
5
0.0 -0.6 -1.2 -1.8
70%
Fig. 2.14.
Same as Fig. 2.13, but for
star cluster models without extinction
added to their photometry, E(B −V ) =
0.
randomly reddened in the range E(B −V ) = [0, 1]. As before, the pho-
tometric errors for UBV RI, JHK and GALEX passbands were σ = 0.05,
0.1, and 0.15 mag, respectively.
Fig. 2.13 (a) shows the results obtained for clusters studied using
UBV RI photometry. Concerning the age, we still see the age-extinction
degeneracy streaks perpendicular to the one-to-one black dashed line, which
extends diﬀerently depending on the true metallicity of clusters.
In Fig. 2.12 (a), the age-extinction degeneracy exists for each given SSP
59
with ﬁxed metallicity. When we derive the cluster parameters allowing all
metallicities, we see that the age-extinction degeneracy now extends be-
tween SSPs (and also between the discrete model distributions) of diﬀerent
metallicities, enlarging the uncertainty in deriving these parameters.
In addition to the reinforced age-extinction degeneracy, deriving the me-
tallicity is complicated by the fact that in the optical passbands the SSPs
(or the discrete model distributions of corresponding age) are naturally close
and overlapping for young and intermediate-age clusters, so that the dis-
tance between them in photometric space is small compared with typical
photometric uncertainties. These two problems make the UBV RI photo-
metric system unsuitable in deriving the metallicity.
In Fig. 2.13, we deﬁne regions around the true metallicities (shaded area
±2 bins around the vertical line in bottom panels), in which we quantify
how many solutions are found in these regions. For example, for clusters
with true metallicity [M/H] = −0.6 (central case of Fig. 2.13 a), only ∼20%
of clusters are classiﬁed with a metallicity in the region around the true
metallicity when only UBV RI is used. The accumulation of solutions at
the metallicity range boundaries can be interpreted as that the derived
metallicity of these clusters could be located even farther away from the
true values, if the range of metallicities were broader.
Fig. 2.13 (b) shows the results of the same clusters, now studied with
UBV RI +JHK photometry. The change compared with the UBV RI case
is the reduction of the dispersion in age and extinction panels. Concerning
the metallicity derivation, the clusters are still suﬀering from metallicity
boundary eﬀects, but the eﬀect is reduced, the metallicity is derived slightly
better. For example, ∼35% of clusters with true metallicity [M/H] = −0.6
are classiﬁed with a metallicity within the good region.
And ∼60% of
clusters with true metallicity [M/H] = −2 are classiﬁed correctly, much
better than in the case with UBV RI photometry alone. In the UBV RI +
JHK case, the strong degeneracy with boundary metallicity [M/H] = 0.2
almost vanishes.
Fig. 2.13 (c) shows the results of the same clusters, now studied with
GALEX + UBV RI photometry. Now, derived and true parameters agree
much better. As in the one–[M/H] vs one–[M/H] tests of the previous sec-
60
tion, the age panels show that adding ultraviolet information completely
discards the streaks perpendicular to the one-to-one black dashed line.
Fig. 2.12 (b) shows that young clusters cannot be degenerated with old clus-
ters through the age-extinction degeneracy, which facilitates the age and
mass derivation. The scatter around the true mass is also more strongly
reduced than for UBV RI and UBV RI +JHK cases. The metallicities are
now better derived as well, even when the true metallicity is [M/H] = −0.6,
the boundary eﬀects are signiﬁcantly reduced. Moreover, at least half of the
clusters are classiﬁed with the correct metallicity when ultraviolet data are
added to the optical. In Fig. 2.12 (b) and (c), the SSPs (and also the dis-
crete model distributions) overlap much less than in the optical passbands.
In Fig. 2.12 (c), the combination of far-ultraviolet with optical U passband
allows us to distinguish between diﬀerent metallicities, as the reddening
vector is now nearly parallel to the SSPs (especially at young ages) and
that the SSPs are more spaced, compared with the error bars (see the zoom
plot). It is also interesting to note that, because the reddening vector points
in diﬀerent directions in Fig. 2.12 (b) and (c), it is not possible to degener-
ate two discrete model distributions of diﬀerent metallicities by means of
extinction.
In Fig. 2.14 the same tests were performed with artiﬁcial clusters without
any extinction added to their photometry (E(B −V ) = 0), and classiﬁed
considering the extinction as a known parameter, leaving only the age,
mass, and metallicity as free parameters. Now, without degeneracies intro-
duced by extinction, the derivation of the other parameters is much more
accurate. For all photometric systems, the eﬀect of the metallicity on the
age derivation manifests itself through a slight shift of the ages above or
below the one-to-one black dashed line. Concerning the metallicity deriva-
tion, one can see that even in this case when there is no extinction, a
consistent derivation of the metallicity with only UBV RI passbands is not
possible, despite a strong decrease of boundary eﬀects on the metallicity,
compared with the case where extinction was included (compare Figs. 2.13
and 2.14). For example, only ∼35% of clusters are classiﬁed in the region
of the correct metallicity when the true metallicity is [M/H] = −0.6. Using
UBV RI + JHK, the metallicity of clusters is better derived than in the
61
7
8
9
10
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
7
8
9
10
log10(t=yr) derived
¡0:6
7
8
9
10
7
8
9
10
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
a)
1
3
5
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
1
3
5
N
¡0:6
3
4
5
1
3
5
3
4
5
log10(M=M ¯) derived
3
4
5
¡2:0
b)
−0.8
−0.4
0.0
0.4
0.8
[M=H]used =0:0
¡0:6
[M=H]true =0:0
¡2:0
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡E(B¡V) true
¡0:6
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
7
8
9
10
log10(t=yr) true
7
8
9
10
¡2:0
c)
Fig. 2.15. Age (panel a), mass (panel b)
and extinction (panel c) derived for a sam-
ple of 10 000 artiﬁcial star clusters with true
mass log10(M/M⊙) = 4 using WFC3 pho-
tometry with σ = 0.05 mag for the photo-
metric Gaussian errors on each passband.
On each block of panels, the metallicity of
the models is speciﬁed on the right and the
metallicity of the grid used to classify the
clusters is speciﬁed on the top.
case with unknown extinction, and the metallicity boundary eﬀects are de-
creased. In the worst case, at least ∼55% of clusters are classiﬁed with a
correct metallicity. Hence, the break of degeneracies with metallicity can
be eﬃciently achieved with UBV RI +JHK photometric system only when
the extinction is well constrained beforehand. For GALEX + UBV RI, the
metallicity prediction only slightly improves when there is no extinction,
compared with the case when there is extinction.
62
2.6
Exploration of the metallicity eﬀects for the
WFC3 photometric system onboard HST
2.6.1
One–metallicity vs one–metallicity test
We apply the method of star cluster parameter derivation using the
WFC3 photometric system: UVIS1/F275W, UVIS1/F336W, ACS/F475W,
ACS/F814W, IR/F110W and IR/F160W to characterize the ability of this
photometric system to derive the physical parameters of clusters. We study
this particular photometric system because a M31 star cluster sample with
photometry obtained in this system will be studied in Section 3.2.
The
photometric passbands of this photometric systems can be seen in bot-
tom panel of Fig. 2.11, where they are compared to the passbands of the
UBV RI+JHK and GALEX ones (central panel).
We generated 3 samples of 10 000 artiﬁcial star clusters with uniform ran-
dom age in the range log10(t/yr) = [6.6, 10.2], mass ﬁxed to log10(M/M⊙)
= 4, with uniform random extinction in the range E(B −V ) = [0, 1]. Each
of the 3 samples has a ﬁxed metallicity, [M/H] = 0, −0.6, or −2. Gaussian
photometric errors of σ = 0.05 mag were added to the magnitudes of the
artiﬁcial clusters for each passband.
In this test we derived the age, mass, and extinction of clusters using
model grids of ﬁxed metallicity ([M/H] = 0, −0.6, or −2), and the results are
displayed in Fig. 2.15. Comparing Fig. 2.15 to pure optical case (UBV RI)
or optical + NIR case (UBV RI +JHK) shown in Section 2.4, the presence
of the UV passband (here UVIS1/F275W) helps signiﬁcantly to narrow
the scatter in derived age, mass, and extinction for main diagonal panels
(where the metallicity of the used grid is the same as the true metallicity)
as well as for out-of-diagonal panels (where the metallicities are diﬀerent).
In the latter case, the similar metallicity eﬀects are seen as in Section 2.4,
producing oﬀsets on the age and mass, and increasing the scatter in the
extinction.
63
2.6.2
One–metallicity vs whole metallicity range: taking
metallicity eﬀects into account
In this test we derive the age, mass, extinction, and metallicity of the same
artiﬁcial clusters of ﬁxed metallicity, but here using a model grid containing
13 metallicities (from [M/H] = 0.2 to −2.2) in order to check the ability
of the method to constrain the metallicity too. We studied the clusters
allowing three diﬀerent amounts of photometric errors in order to study
their inﬂuence on the derivation of parameters: Gaussian photometric errors
of σ = 0.03, 0.05, and 0.1 mag were added to each magnitude.
Fig. 2.16 shows the results; the block of panels (b) can be compared to
the results shown in Fig. 2.13, as the same amount of photometric error has
been added to artiﬁcial cluster photometry. The presence of the ultravio-
let F275W passband of the WFC3 photometric system is important as it
helps to signiﬁcantly reduce the biases in parameter derivation, including
metallicity, compared to the UBV RI photometric system.
Concerning the amount of photometric errors, in Fig. 2.16 we see a much
larger agreement between derived and true parameters for low and medium
amount of added photometric errors. When the photometric errors reach
0.1 mag, the scatter around true age and extinction is strongly increased.
Also, the metallicity of artiﬁcial clusters with the true metallicity [M/H] =
−0.6 is well derived only when the photometric accuracy is no larger than
0.05 mag. The better the photometric accuracy, the higher the accuracy of
the derived metallicity can be achieved with the WFC3 passbands what is
emphasized in the Section 3.2 by use of real data.
64
7
8
9
10
7
8
9
10
log10(t=yr) derived
a)
Photometric errors : 0:03 mag
[M=H]true =0:0
3
4
5
1
3
5
N
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡true
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
80%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) derived
7
8
9
10
log10(t=yr) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
60%
7
8
9
10
¡2:0
3
4
5
7
8
9
10
0.0 -0.6 -1.2 -1.8
75%
7
8
9
10
7
8
9
10
log10(t=yr) derived
b)
Photometric errors : 0:05 mag
[M=H]true =0:0
3
4
5
1
3
5
N
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡true
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
75%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) derived
7
8
9
10
log10(t=yr) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
45%
7
8
9
10
¡2:0
3
4
5
7
8
9
10
0.0 -0.6 -1.2 -1.8
70%
7
8
9
10
7
8
9
10
log10(t=yr) derived
c)
Photometric errors : 0:10 mag
[M=H]true =0:0
3
4
5
1
3
5
N
7
8
9
10
−0.8
−0.4
0.0
0.4
0.8
E(B¡V) derived¡true
0.0 -0.6 -1.2 -1.8
0.0
0.1
0.2
0.3
0.4
0.5
N
70%
7
8
9
10
log10(t=yr) true
¡0:6
3
4
5
log10(M=M ¯) derived
7
8
9
10
log10(t=yr) true
0.0 -0.6 -1.2 -1.8
[M=H] derived
30%
7
8
9
10
¡2:0
3
4
5
7
8
9
10
0.0 -0.6 -1.2 -1.8
60%
Fig. 2.16.
Age, mass, extinc-
tion and metallicity derived for a
sample of 10 000 artiﬁcial star clus-
ters of true mass log10(M/M⊙) =
4, with σ = 0.03 mag of Gaus-
sian photometric errors (left pan-
els), 0.05 mag (central panels), and
0.1 mag (right panels). The meta-
llicity of the clusters is indicated
on the top of each block of panels.
These results are obtained using
WFC3 broad-band photometry.
65
66
Chapter 3
Application to real Star Clusters
3.1
The M31 galaxy star cluster sample of Van-
sevičius et al. (2009)
A star cluster catalog of 285 objects located in the south-west ﬁeld of
the M31 galaxy was compiled by Narbutis et al. (2008) using the deep
BV RI and Hα photometry from the Subaru telescope, as well as multi-
band maps based on HST, GALEX, Spitzer, and 2MASS imaging. The
UBV RI photometry was derived using the Local Group Galaxy Survey
data from Massey et al. (2006). The magnitude limit of the cluster sample
was set to V = 20.5 mag.
Vansevičius et al. (2009) selected 238 clusters from that sample, exclud-
ing the ones with strong Hα emission, and compared their multiband colors
to PEGASE (Fioc & Rocca-Volmerange 1997) SSP models to derive their
age, mass, metallicity, and extinction. The selected clusters are shown in
Fig. 3.1. The Spitzer data were used to constrain the maximum extinction
for each cluster. They reported ∼30 classical globular clusters with low
metallicity and older than 3 Gyr.
The remaining ∼210 younger clusters
were classiﬁed as objects belonging to the disk, with average metallicity
[M/H] = −0.4. Figure 3.2 shows the U −B vs B −V and U −V vs R −I
diagrams of the 238 star clusters from Vansevičius et al. (2009), compared
to the grid of star cluster models built in Section 1.4.
Working with a grid of models with single metallicity, [M/H] = −0.4,
we attempted to exclude more metal-rich clusters from Vansevičius et al.
(2009) sample by only selecting objects with galactocentric distance over 7
kpc. This subsample consists of 216 clusters and is displayed in Fig. 3.2. It
is studied with our method described in Section 2.1, using the Milky Way
standard extinction law (Cardelli et al. 1989) and distance modulus to M31
of (m −M)0 = 24.47 derived by McConnachie et al. (2005).
67
N
E
Fig. 3.1. Positions of M31 PHAT clusters, shown in Spitzer maps (24 µm). The red
dots are the PHAT cluster sample, and the blue star symbols are the Vansevičius et al.
(2009) sample.
Figure 3.3 presents the age (panels a, b, c), mass (panels d, e, f) and
extinction (g, h, i) of 211 clusters (from the 216 sample) derived by using
our method; for ﬁve clusters, no model was found within the 3–σ around
the observed magnitudes. Clusters were studied twice, ﬁrst with a narrow
extinction range E(B −V ) = [0.04, 0.5] allowed in the model grid, and
second with a wider one, [0.04, 1.0].
The ﬁrst column (panels a, d, g)
compares the age, mass, and extinction derived when a narrow extinction
range is allowed vs the Vansevičius et al. (2009) results. The second column
(panels b, e, h) compares the age, mass, and extinction derived when a wide
extinction range is allowed vs the Vansevičius et al. (2009) results. The last
column (panels c, f, i) compares the results obtained with a wide extinction
range allowed vs the ones obtained with a narrow extinction range allowed.
In Fig. 3.3 (a), when clusters are studied in a narrow allowed extinction
range, E(B −V ) = [0.04, 0.5], the derived ages show the same features
as the models studied in Fig. 2.5 (d), reproduced here in the background of
the panel. The degeneracy streaks develop above and below the one-to-one
line, perpendicularly to it, and are marked by ellipses numbered “1” and
“2” in Fig. 3.3 (a). As for the models in the background, the upper degen-
eracy streak concerns clusters with overestimated age and underestimated
extinction, shown by ellipse “1” in Fig. 3.3 (g). In contrast, for the lower
degeneracy streak (ellipse “2”), the age is underestimated and extinction is
overestimated. Since the upper streak (ellipse “1”) is more developed than
the lower one (“2”), we interpret that as a result of a too narrow extinction
range in the model grid allowed, E(B −V ) = [0.04, 0.5].
68
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
Fig. 3.2. M31 galaxy star cluster sample of 238 objects from Vansevičius et al. (2009)
(circles and star symbols) and the sample of 216 objects studied (star symbols) having
galactocentric distance over 7 kpc. Panels show: (a) U −B vs B −V and (b) U −V
vs R −I diagrams. The model grid (without extinction) used to derive the physical
parameters of clusters is displayed in the background with indicated reddening vectors
following the Galactic extinction law.
The continuous line traces PADOVA SSP of
[M/H] = −0.4.
In Fig. 3.3 (b), when clusters are studied in a wider model extinction
range, E(B −V ) = [0.04, 1], the upper degeneracy streak is less popu-
lated, and the lower one extends, meaning that some of the clusters have
overestimated extinction (ellipse “3”), also shown in panel (h).
If the intrinsic range of extinction for a cluster sample is wide, as in the
galaxy M31, then a narrow extinction range of models produces an extended
upper streak (ellipse “1”) and a smaller lower streak (ellipse “2”), shown in
Fig. 3.3 (a). In panel (b), when the allowed extinction range of models is
wide, the upper streak retracts and the lower streak develops. We conclude
that in a galaxy with wide extinction range, it is not possible to derive
the parameters for the clusters aﬀected by age-extinction degeneracy and
additional constraints for the extinction are needed; e.g., Vansevičius et al.
(2009) used a Spitzer emission map, to trace the dust lanes of M31 and to
reduce the age-extinction degeneracy.
Figs. 3.3 (d, e) show that for high-mass clusters we obtain lower masses
than those given by Vansevičius et al. (2009). Inspecting the metallicity
values provided by Vansevičius et al. (2009), we note that high-mass clusters
have metallicities lower than the [M/H] = −0.4 used in our model grid.
69
−
(
)
E B
V
10
9
8
7
log   ( / yr) from V09
   t
log   ( / yr) from V09
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
log   ( / yr), (
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
5
4
3
−
=
log   (M/ M  ), (
)
[0.04,0.5]
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
log   ( / yr)
   t
10
log   (M/ M  )
10
10
10
10
log   (M/ M  ) from V09
10
log   (M/ M  ) from V09
10
10
Fig. 3.3.
M31: age, mass, and extinction of 211 star clusters from (Vansevičius
et al. 2009, referred to as V09).
Panels (a, d, g) show the results when a narrow
extinction range, E(B −V ) = [0.04, 0.5], is allowed in the model grid, compared to
V09 values.
Panels (b, e, h) show the results for a wider allowed extinction range,
[0.04, 1.0], compared to V09 values. Panels (c, f, i) compare the results obtained in a
wide extinction range vs the ones obtained in a narrow extinction range. In panels (a,
b, c), a density map of Fig. 2.5 (d) is reproduced to show the regions of age-extinction
degeneracy.
Error bars are computed as described in Section 2.1.
Six clusters from
V09, which have E(B −V ) > 1, are not shown in panels (g) and (h). Dashed ellipses,
numbered “1”, “2”, and “3”, describe the majority of associated clusters in the age and
extinction panels.
70
This could be a sign of the metallicity eﬀect on the derivation of physical
parameters.
3.2
The
M31
galaxy
star
cluster
sample
of
PHAT survey
Using the WFC3+ACS photometric system on board HST, the Panchro-
matic Hubble Andromeda Treasury (PHAT) team (see, e.g., Dalcanton et al.
2012; Beerman et al. 2012; Weisz et al. 2013) performed a survey of 1/3 of
the M31 galaxy (the north-east region), providing a large catalog of 601
clusters (Johnson et al. 2012), shown in Fig. 3.1. This catalog of star clus-
ters was already analyzed by Fouesneau et al. (2014), who derived their
age, mass, and extinction. They used a constant solar metallicity through
the whole M31 disk, arguing that the HII zone study (Zurita & Bresolin
2012) does not show any signiﬁcant metallicity gradient. They allowed four
diﬀerent metallicities ([M/H] = −0.7, −0.4, 0.0, and +0.4, i.e., from Small
Magellanic Cloud to super-solar metallicities) for 30 massive globular-like
clusters with mass > 105M⊙.
We ﬁrst selected a sample of 402 clusters from the catalog of Johnson
et al. (2012) with available magnitudes in all photometric passbands. Then
from this sample we selected two cluster groups, for which we display the
photometric accuracy for each passband in Fig. 3.4. In cluster group 1 (65
objects, the large ﬁlled dots in Fig. 3.4), the photometric accuracy of objects
is < 0.15 mag in F275W and F336W, < 0.1 mag in F475W and F814W, and
< 0.2 mag in F110W and F160W. In cluster group 2 (138 objects, the large
open dots in Fig. 3.4), the photometric accuracy in each passband is < 0.5
mag. In total, we analyze 203 clusters. In Fig. 3.4 we indicate for each
passband the number of objects from the 203 clusters for which photometry
is more accurate than 0.03, 0.05, 0.1 mag.
We derived the parameters of both cluster groups by ﬁrstly ﬁxing the
metallicity of all clusters to the solar value, and a second time by allowing a
large range of metallicities in the model grid with 13 values of [M/H] = +0.2
to −2.2, in steps of 0.2.
The color-color diagrams of cluster groups 1 and 2 are shown in Fig. 3.5
71
16
20
24
F275W [mag]
0.0
0.4
0.8
eF275W [mag]
a)
<0:10 : 102
<0:05 : 55
<0:03 : 31
16
20
24
F336W [mag]
0.0
0.4
0.8
eF336W [mag]
b)
<0:10 : 166
<0:05 : 97
<0:03 : 55
16
20
24
F475W [mag]
0.0
0.4
0.8
eF475W [mag]
c)
<0:10 : 184
<0:05 : 111
<0:03 : 62
12
16
20
24
F814W [mag]
0.0
0.4
0.8
eF814W [mag]
d)
<0:10 : 119
<0:05 : 64
<0:03 : 27
12
16
20
24
F110W [mag]
0.0
0.4
0.8
eF110W [mag]
e)
<0:10 : 90
<0:05 : 46
<0:03 : 23
12
16
20
24
F160W [mag]
0.0
0.4
0.8
eF160W [mag]
f)
<0:10 : 74
<0:05 : 34
<0:03 : 12
Fig. 3.4. Photometric accuracy of the sample of 402 clusters (all dots) selected with
available photometry in all passbands from the Johnson et al. (2012) catalog. Group
1 clusters (65 objects, large ﬁlled dots) have the upper limit of the accuracy indicated
by long dashed lines in diﬀerent passbands. Group 2 clusters (138 objects, large open
dots) have accuracy < 0.5 mag (short dashed lines) in all passbands. Small gray dots
designate clusters which are not members of group 1 or group 2 and not further studied
because of too low photometric accuracy (they have accuracy > 0.5 mag in at least one
passband). In each panel we indicate the number of clusters (from the total 203 clusters
of group 1 and group 2) with photometric accuracy better than 0.1, 0.05 and 0.03 mag
in the passband associated with the panel.
in optical-only passbands (panel a), and UV-optical-IR passbands (panel
b), along with the SSP evolutionary tracks (tracing the age of clusters,
valid for massive clusters only) of three metallicities as an illustration. In
this ﬁgure, one can guess the advantage of using UV and IR photometry
to derive the cluster metallicity. In panel a), with optical-only passbands,
we see that the SSPs are rather close, while this is not the case anymore
in panel b), where UV and IR passbands are shown. This indicates that,
at least for massive and old clusters (center to bottom of panel b), the
derivation of metallicity is possible with the WFC3+ACS system, provided
that the photometric accuracy is reasonable, such as for group 1 clusters
(for which the maximum photometric accuracy is indicated in Fig. 3.5).
72
−0.5
0.5
1.5
2.5
F475W¡F814W [mag]
−1.5
−0.5
0.5
1.5
F336W¡F475W [mag]
a)
−0.5
0.5
1.5
2.5
F814W¡F110W [mag]
−0.5
0.5
1.5
2.5
F275W¡F336W [mag]
b)
Fig. 3.5. Color-color diagrams of the 65 group 1 clusters (ﬁlled dots) and 138 group 2
clusters (open dots) deﬁned in Fig. 3.4. Panel (a) shows the situation in optical colors
only, while panel (b) shows the situation when we make use of the ultraviolet and near-
infrared passbands. In both panels, the error bars indicate the maximum photometric
error for the group 1 clusters. The three lines show SSP evolutionary tracks of metallicity
[M/H] = 0 (dotted line), −1 (dashed line), and −2 (solid line). The SSP ages extend
from log10(t/yr) = 6.6, in the upper part of each panel, to 10.1 in the lower part of each
panel. The arrows indicate the direction of the extinction AV = 1 mag.
3.2.1
Results with ﬁxed solar metallicity
The age, mass, and extinction derived with the ﬁxed metallicity grid
[M/H] = 0 are compared to the results of Fouesneau et al. (2014) in the
ﬁrst row of Fig. 3.6. In general, a satisfactory agreement is observed for the
majority of clusters between the parameters derived in this study and those
supplied by Fouesneau et al. (2014), except for a few objects. There are
two reasons for the deviating clusters: (1) for 30 old and massive clusters,
Fouesneau et al. (2014) derived the parameters, leaving the metallicity free
to vary in the range [M/H]= [−0.7,0.4], while we used a ﬁxed solar metalli-
city, and (2) the stellar models used to derive the cluster parameters were
very diﬀerent. Indeed, PEGASE-based (Fioc & Rocca-Volmerange 1999)
stellar models used by Fouesneau et al. (2014) are based on the Bertelli
et al. (1994) stellar models with a simpliﬁed analytic description of Groe-
newegen & de Jong (1993) for the TP-AGB phase, while PADOVA stellar
models used here attempt to numerically reproduce the physics of that stel-
lar phase (see Marigo et al. 2008; Girardi et al. 2010). For the masses,
Fouesneau et al. (2014) provide the present-day mass, while the masses
output by our method are initial masses, causing a natural slight shift be-
73
6
8
10
log10(t=yr)Fouesneau
6
8
10
log10(t=yr)[M=H] =0:0
a)
1
2
3
4
5
2
4
6
log10(M=M ¯)Fouesneau
2
4
6
log10(M=M ¯)[M=H] =0:0
b)
1
2
3
4
5
0.
0.4
0.8
E(B¡V)Fouesneau
0.
0.4
0.8
E(B¡V)[M=H] =0:0
c)
1
2
3
4
5
Fig. 3.6. Age, mass, and extinction derived with ﬁxed solar metallicity grid vs
the results of Fouesneau et al. (2014). Filled dots are the 65 clusters of group
1 and open dots are the 138 clusters of group 2, which are speciﬁed in Fig. 3.4.
Clusters marked 1–5 in this ﬁgure and Figs. 3.7 and 3.8 are the same objects.
6
8
10
log10(t=yr)[M=H] =0:0
6
8
10
log10(t=yr)[M=H] free
a)
1
2
3
4
5
2
4
6
log10(M=M ¯)[M=H] =0:0
2
4
6
log10(M=M ¯)[M=H] free
b)
1
2
3
4
5
0.
0.4
0.8
E(B¡V)[M=H] =0:0
0.
0.4
0.8
E(B¡V)[M=H] free
c)
1
2
3
4
5
Fig. 3.7.
Age, mass, and extinction using free metallicity grid vs the results
derived using a model grid of ﬁxed solar metallicity. Filled dots are the 65 clusters
of group 1 and open dots are the 138 clusters of group 2, which are speciﬁed in
Fig. 3.4. Clusters marked 1–5 in this ﬁgure and Figs. 3.6 and 3.8 are the same
objects.
tween their mass predictions and our mass predictions. The four clusters of
group 1 (Fig. 3.6b; ﬁlled points) strongly below the identity line and classi-
ﬁed as massive by Fouesneau et al. (2014) are in fact globular-like clusters1,
wrongly classiﬁed by our method when the metallicity is ﬁxed to the solar
value in the model grid. We provide more details on them in the following
sections.
3.2.2
Results with free metallicity
Parameters derived when metallicity is left free are shown in Fig. 3.7. As
expected from artiﬁcial tests, the introduction of the free metallicity pa-
rameter introduces a new level of complexity. Here we compare the age,
mass, and extinction derived when metallicity is left free versus the same
1Veriﬁed inspecting the images provided by PHAT: http://archive.stsci.edu/pub/hlsp/phat/
74
4.5
5.5
6.5
log10(M=M ¯)Caldwell
4.5
5.5
6.5
log10(M=M ¯)derived
a)
1
2
3
4
5
−2.5
−1.5
−0.5
0.5
[Fe=H]Caldwell
−2.5
−1.5
−0.5
0.5
[M=H]derived
b)
1
2
3
4
5
4.5
5.5
6.5
log10(M=M ¯)Caldwell
-1
0
1
[M=H]derived¡[Fe=H]Caldwell
c)
1
2
3
4
5
Fig. 3.8. Our results vs those of Caldwell et al. (2011) for the 36 common massive
clusters, shown for the mass (panel a), and the metallicity (panel b). Panel (c) shows
the diﬀerence in metallicity between this work and Caldwell et al. (2011) values vs the
cluster mass. For the panel (c), the error bars of Caldwell et al. (2011) and derived here
are summed quadratically. Filled dots are the group 1 clusters and open dots are the
group 2 clusters, as deﬁned in Fig. 3.4. Clusters marked 1–5 in this ﬁgure and Figs. 3.6
and 3.7 are the same objects.
parameters when the metallicity is ﬁxed to the solar value.
Many clusters seen as young or middle-aged in metal-ﬁxed case are now
seen as older. For example, the ﬁve points in the top left corner of the
age panel (Fig. 3.7 a, four of which are the ﬁlled points below the identity
line in Fig. 3.6 b) are seen as young in the case where metallicity is ﬁxed
to solar value, but old in the case where metallicity is left free.
They
are also more massive, located well above the identity line in the mass
panel Fig. 3.7 (b). These ﬁve objects are classiﬁed as of low-metallicity when
the metallicity is left free, which is also found likely when inspecting the
images, as they are brighter in the F275W and F336W passbands than
other globular-like clusters classiﬁed with higher metallicity. We used the
individual cluster pictures in the six WFC3+ACS passbands and also Sloan
Digital Sky Survey (SDSS), Two Micron All Sky Survey (2MASS), and
Galaxy Evolution Explorer (GALEX) images available through ALADIN2
Sky Altas to conﬁrm that these objects are really globular-like clusters,
and not young low-mass clusters. These ﬁve objects, with given PHAT ID
1439, 428, 680, 683, and 1396, are also conﬁrmed as globular clusters in
the Revised Bologna Catalog (2012, version 5, see also Galleti et al. 2004)
with the designation B064D-NB6, B229-G282, B165-G218, B167-G212, and
NB21-AU5, indicated from 1 to 5 respectively in the Figs. 3.6, 3.7, and 3.8.
2http://aladin.u-strasbg.fr/
75
7
8
9
10
log10(t=yr)
2
3
4
5
6
7
log10(M=M ¯)
7
8
9
10
log10(t=yr)
0
0.4
0.8
1.2
E(B¡V)
2
3
4
5
6
7
log10(M=M ¯)
0
0.4
0.8
1.2
E(B¡V)
7
8
9
10
log10(t=yr)
+0.2
-0.6
-1.4
-2.2
[M=H]
0
0.4
0.8
1.2
E(B¡V)
+0.2
-0.6
-1.4
-2.2
[M=H]
2
3
4
5
6
7
log10(M=M ¯)
+0.2
-0.6
-1.4
-2.2
[M=H]
Fig. 3.9. Two–dimensional marginalized likelihood Lnode (see Eq. 2.2) parameter maps
derived with free metallicity model grid for the cluster ID 428 (B229-G282 in Revised
Bologna Catalog V5, Galleti et al. 2004, indicated as “2” in Figs. 3.6, 3.7, and 3.8) using
photometry taken from Johnson et al. (2012) catalog. The white points indicate the
maximum Lnode in the 4–dimensional parameter space, while the black points show the
solution when the metallicity is ﬁxed to solar value. The white contour lines contain 68%
(solid line), 95% (long-dashed line), and 99% (short-dashed line) of the marginalized
likelihood.
As an illustration, 2–dimensional marginalized likelihood maps are
shown for one of these objects, ID 428 (indicated as “2” in the Figs. 3.6,
3.7, and 3.8), in Fig. 3.9.
The likelihood maps are given for the cluster
classiﬁcation using all 13 metallicities of the model grid.
The parame-
ters derived taking the maximum of likelihood Lnode (see Eq. 2.2) in the
4–dimensional model grid are indicated with the white points in the 2–
dimensional marginalized likelihood maps.
Additionally, the black dots
indicate the parameters obtained when the metallicity is ﬁxed to the solar
value in the model grid (hence reduced to a 3–dimensional grid), resulting
in a wrongly classiﬁed younger, lower-mass, and much more extincted solu-
tion. For this object, ID 428, Fouesneau et al. (2014) as well as our results
when metallicity is ﬁxed to solar value give a too young age and a too low
mass. Our results derived with free metallicity show that this object is an
old massive globular-like cluster, and visual inspection of the HST images
76
Fig. 3.10.
View of the cluster ID 428 (B229-G282 in Revised Bologna Catalog V5,
Galleti et al. 2004, indicated as “2” in the Figs. 3.6, 3.7, and 3.8) in the 6 WFC3
passbands, SDSS, GALEX, and 2MASS through the ALADIN Sky Atlas. The resolved
WFC3 images show unambiguously a globular-like cluster.
shown in Fig. 3.10 through the ALADIN Sky Atlas conﬁrms clearly that
this object is a globular-like cluster.
We note that in Fig. 3.7 (a) a dozen of the objects with ages, derived
adopting a ﬁxed solar metallicity, around log10(t/yr) = 8, have overesti-
mated ages when derived with free metallicities. This is very likely because
these objects are relatively faint, with poor photometric accuracy, and are
contaminated by bright red background stars. However, a careful analy-
sis of the WFC3+ACS object images and their likelihood maps (similar to
those shown in Fig. 3.9) allows us to resolve degeneracies in most of the
cases.
Recently, Caldwell et al. (2011) produced the spectroscopic study of
old star clusters of M31 galaxy, using the Lick indices to derive their age,
mass, extinction, and metallicity. To check the reliability of our derived
metallicity, we compare those of the 36 clusters common to the Caldwell
et al. (2011) sample and the clusters analyzed in this study in Fig. 3.8.
As Caldwell et al. (2011) ﬁxed the age of most of the clusters to 14 Gyr,
77
−2
−1
0
[M=H]
0
20
40
N
a) log10(t=yr) <9
−2
−1
0
[M=H]
b) log10(t=yr)⩾9
Fig.
3.11.
The derived
metallicity
of
clusters
with
ages lower than 1 Gyr (panel
a), and of clusters with ages
higher than 1 Gyr (panel b) for
group 1 (thick line) and group
2 (thin line).
here we only compare the mass and metallicity of the clusters. Again, an
overall agreement is found between the parameters. The accuracy of our
photometric metallicity derivation is linked to the mass, and thus very likely
to the signal-to-noise of available photometry for each object, as the scatter
seen in Fig. 3.8 (c) is increasing with decreasing star cluster mass. The ﬁve
clusters studied above are also indicated in Fig. 3.8, where one can see that
the metallicity derived using our method coincides well with that of the
spectroscopic method of Caldwell et al. (2011).
In Fig. 3.11, we show the histograms of derived metallicity for young age
clusters (log10(t/yr) < 9, panel a) and old age clusters (log10(t/yr) ⩾9,
panel b) of group 1 (thick line) and group 2 (thin line).
Most of the
young clusters are classiﬁed as metal-rich, while the old cluster metallic-
ities are more dispersed. Note, that even for low photometric accuracy,
Fig. 3.11 (a) still tells us that the clusters are more likely metal-rich than
metal-poor.
Also, it is interesting to compare Fig. 3.11 (a) to the artiﬁ-
cial tests of Fig. 2.16, in the case of the worst photometric accuracy (panel
c block). Indeed, we see a strong similarity between the case with true
[M/H] = 0 and the left panel of Fig. 3.11. Therefore, ﬁxing the metallicity
to a value as high as the solar value assumed by Fouesneau et al. (2014) is
likely a good choice for most of the young M31 clusters. Note that Caldwell
et al. (2009) recommends supersolar metallicities for young M31 clusters,
although they did not derive individual metallicities for young clusters.
78
3.3
Application to the M33 star clusters
3.3.1
Why M33?
There is a current need for an accurate catalog for the star cluster system
of the Triangulum galaxy, or Messier 33 (M33), as it could be used as a
constraint on the derivation of star formation history in this galaxy. Several
other reasons encourage the study of this particular star cluster system. The
nearly face-on inclination (i = 56 degrees, Regan & Vogel 1994) of M33
reduces extinction eﬀects for the majority of its cluster population, situated
in the disk. Also, M33 is the only close late-type spiral galaxy, situated at
a distance of 867 kpc (Galleti et al. 2004, distance modulus of (m −M)0 =
24.69), making its star cluster system accessible to ground-based telescopes
for integrated photometric and spectroscopic studies and to the Hubble
Space Telescope (HST) for resolved measurements. While other star cluster
systems of the Local Group galaxies have received considerable attention,
as in the case of M31 and the Magellanic Clouds, the M33 star cluster
system has not been studied as much. Therefore, an extended knowledge of
its star cluster system would improve the understanding of the relationship
between star clusters and their host galaxies.
The M33 star cluster system has nevertheless been studied for a long
time.
Several teams (Hiltner 1960; Kron & Mayall 1960; Melnick &
D’Odorico 1978; Christian & Schommer 1982, 1988; Mochejska et al. 1998)
contributed to the building of a catalog of star clusters in M33 using
ground-based unresolved photometry in optical passbands. Chandar et al.
(1999a,b,c, 2001) used the WFPC2 camera onboard HST to detect 102 ad-
ditional clusters. They derived their physical parameters using integrated
photometry that were compared with SSP models, which are ideal star clus-
ter models in the sense that they are based on a continuously sampled IMF
(see Chapter 1). Sarajedini et al. (1998, 2000, 2007) also used WFPC2 and
ACS images, but derived the parameters using resolved color-magnitude
diagrams for the most massive clusters. All studies before 2007 have been
combined in a merged catalog by Sarajedini & Mancone (2007).
More recently, studies in the literature continue to use the SSP models
to derive the physical parameters of the M33 clusters (age, mass, extinction,
79
23.2
23.4
23.6
23.8
α [deg]
30.2
30.4
30.6
30.8
31.0
31.2
δ [deg] 
Fig.
3.12.
The dif-
ferent catalogs of clusters
used:
Fan & de Grijs
(2014) shown as open red
circles, Ma (2012, 2013)
as open blue squares, San
Roman et al. (2010) as
green diamonds, San Ro-
man et al. (2009) as vi-
olet crosses.
The three
dashed ellipses have semi-
major axes of 10′, 20′, and
30′ to the center (marked
as a large black plus sym-
bol) and can be seen as
circles of the same radii
projected on the M33 disk.
and metallicity). However, as presented in Sections 1.1 and 1.2, it is know
well known that these models are oversimpliﬁed and biased, as they do not
take the natural dispersion of integrated colors of star clusters into account,
the stochasticity problem. In this Section, we aim to study the M33 star
cluster system with the star cluster models that takes the stochasticity
problem into account.
3.3.2
The M33 star cluster catalog
Recently San Roman et al. (2010) observed 803 M33 star clusters (599
candidates and 204 conﬁrmed using the HST) using the 3.6 m Canada-
France-Hawaii-Telescope (CFHT) and published a catalog in the MegaCam
camera u∗g′r′i′z′ photometric system. Although their catalog also contained
the cluster photometry converted to the ugriz photometric system of the
Sloan Digital Sky Survey (SDSS), we considered here the native MegaCam
photometric system to avoid likely conversion approximation.
Using archival images of the Local Group Galaxies Survey (LGGS,
Massey et al. 2006) obtained using the 4 m Kitt Peak National Observatory
80
15
16
17
18
19
20
21
22
VMa
-1
0
1
¢(U¡V)
15
16
17
18
19
20
21
22
VMa
-1
0
1
¢(B¡V)
15
16
17
18
19
20
21
22
VMa
-1
0
1
¢V
15
16
17
18
19
20
21
22
VMa
-1
0
1
¢(V¡R)
15
16
17
18
19
20
21
22
VMa
-1
0
1
¢(V¡I)
Fig. 3.13. Diﬀerences in the sense Fan & de Grijs (2014) photometry minus Ma (2012)
(red) and Ma (2013) (blue) photometries.
81
telescope, Ma (2012) built a catalog of 392 clusters, and Ma (2013) added
234 others, all in the standard UBV RI photometric system. Fan & de Grijs
(2014) also reanalyzed the LGGS photometry to publish a catalog of 708
clusters. The comparison of the colors from Fan & de Grijs (2014) and Ma
(2012, 2013) is shown in Fig. 3.13. We adopted for the UBV RI photometric
system the Ma (2012, 2013) photometry when available, and the Fan & de
Grijs (2014) photometry for other clusters, correcting the Fan & de Grijs
(2014) photometric zero-points to the Ma (2012, 2013) ones in order to have
a homogeneous catalog. The zero-point correction coeﬃcients were, for Fan
& de Grijs (2014) minus Ma (2012, 2013) photometry: ∆V = −0.099 mag,
∆(U −V ) = −0.091 mag, ∆(B −V ) = −0.066 mag, ∆(V −R) = 0.036 mag,
and ∆(V −I) = 0.086 mag, computed for respectively 289, 208, 208, 250,
and 178 clusters with available photometry in common between Fan & de
Grijs (2014) and Ma (2012, 2013) catalogs.
These catalogs include all objects published in the catalog of star clus-
ters of Sarajedini & Mancone (2007), who merged all the M33 star cluster
catalogs published before 2007. The association of these catalogs in this
paper results in a merged catalog of 910 objects, which is shown in Fig. 3.12
color-coded to show to which original catalog the clusters belong.
We supplemented optical data with near-infrared data by using deep
Two Micron All Sky Survey (2MASS) JHK images3 with exposure times
6 times longer (2MASS 6X) than the standard 2MASS ones. This results
in a photometry approximatively 1.5 mag deeper in 2MASS 6X than pho-
tometry derived from standard 2MASS images. The photometry of clus-
ters was obtained by the use of aperture photometry using the standard
IRAF/digiphot/apphot package with an aperture radius in the range 2′′ to
4′′, and an aperture correction built using the curves of growth of a dozen
relatively isolated clusters. By this process, we derived the JHK photome-
try of 758 clusters. To ensure that the 2MASS 6X images were correctly
calibrated, we also derived aperture photometry of stars, selected in the
same region where clusters are located, and compared this derived aperture
photometry to the stellar aperture photometry provided by the 2MASS
3Kindly made available by T. H. Jarrett, IPAC/Caltech
82
10
14
18
J
2
1
0
1
2
J6X−JPSC
a)
10
14
18
H
2
1
0
1
2
H6X−HPSC
b)
10
14
18
K
2
1
0
1
2
K6X−KPSC
c)
10
14
18
J
0.0
0.2
0.4
0.6
eJ
d)
10
14
18
H
0.0
0.2
0.4
0.6
eH
e)
10
14
18
K
0.0
0.2
0.4
0.6
eK
f)
10
14
18
J
0
50
100
150
N
g)
10
14
18
H
0
50
100
150
N
h)
10
14
18
K
0
50
100
150
N
i)
Fig. 3.14. Top row: black circles show the comparison of the aperture photometry
of stars derived in this work versus the PSC values, and red circles are the comparison
of our aperture photometry of the star clusters versus the PSC values for the 109
clusters for which PSC has aperture photometry. Central row: black squares show the
photometric uncertainties provided by the PSC for 109 clusters and all circles show the
photometric uncertainties derived for our aperture photometry for 758 clusters. The red
circles are 502 clusters with uncertainties lower than the limit of 0.3 mag (dashed line)
in all JHK passbands, and the open circles are the clusters for which the photometry
does not satisfy this criteria. Bottom row: distributions of cluster brightness: white
histograms contain the 758 clusters for which we derived photometry and the gray ones
contain the 502 clusters that satisfy the photometric uncertainty criteria. The thick
open histograms represent the 109 clusters contained in the PSC, for comparison. In
each row, the situation is shown for J (left panels), H (central panels), and K (right
panels) passbands.
83
0
1
2
V−I
1
0
1
2
U−V
a)
0.5
0.0
0.5
1.0
R−I
1
0
1
2
3
U−R
b)
0.5
0.0
0.5
1.0
r′−i′
0.5
0.0
0.5
1.0
g′−r′
c)
1
0
1
r′−z′
1
0
1
2
3
u ∗−r′
d)
Fig. 3.15.
Color-color diagrams of the cluster sample in optical photometric pass-
bands. The upper row of panels shows the color-color diagrams in the standard UBV RI
photometric system and the lower row in the u∗g′r′i′z′. In all panels, the blue circles
are clusters that are bright in UV, cyan circles are clusters faint in UV, white circles
are clusters embedded or close to HII zones, red circles are globular-like clusters and
green star symbols are likely stars rather than clusters. In each panel, the extent and
density of the stochastic star cluster model grid is shown as a density surface (displayed
in logarithmic scale), and the solid line is the SSP model shown for comparison. In both
stochastic and SSP models shown here, the metallicity is [M/H] = −0.4. The mass of
the stochastic cluster models shown here is ﬁxed to log10(M/M⊙) = 3.5, a typical mass
of the low-mass clusters studied in this work, to show the extent of their colors. In each
panel, the black arrow shows the Milky Way extinction law direction and the red arrow
shows the LMC extinction law direction, both computed for AV = 1 mag.
84
2
1
0
1
2
U−V
1
0
1
FUV−NUV
a)
1
0
1
2
u ∗−r′
1
0
1
FUV−NUV
b)
1
0
1
2
J−K
2
1
0
1
2
3
U−V
c)
1
0
1
2
J−K
1
0
1
2
3
u ∗−r′
d)
Fig. 3.16.
Same as in Fig. 3.15, but for GALEX-optical colors (top panels) and
optical-2MASS colors (bottom panels). In top panels, a small part of clusters is shown,
because most of the clusters are too dim in the GALEX passbands, or situated too close
to bright neighboring objects.
Point Source Catalog (2MASS PSC)4, which has been compiled using the
standard 2MASS images. The ﬁrst row of panels in Fig. 3.14 presents the
comparison of aperture photometry of stars derived in this work versus the
aperture photometry provided by PSC (black circles) for the JHK pass-
bands. For most of stars the agreement is satisfactory. We noted that 109
clusters are included in the PSC and we could compare the aperture pho-
tometry that PSC provides for them with our aperture photometry, shown
in red in the ﬁgure. The error bars reﬂect the photometric uncertainties
derived in our aperture photometry. The photometric uncertainties of the
4http://irsa.ipac.caltech.edu
85
758 clusters derived in this work are shown in the central row of Fig. 3.14
(all circles), compared with the uncertainties of the 109 clusters for which
PSC also provides aperture photometry (black squares). As indicated in
the central row of panels of Fig. 3.14 by dashed lines, we will use only
the clusters with photometric uncertainties lower than 0.3 mag in all JHK
passbands. This selection results in 502 clusters with full JHK photome-
try. The bottom row in Fig. 3.14 presents the distribution of the clusters
in each of the JHK passbands of our derived photometry for the whole
sample of 758 clusters (in white) and for the sample of 502 clusters with
uncertainties lower than 0.3 mag in all JHK passbands (in gray), compared
to the distribution of 109 clusters that are included in the PSC (open thick
histogram).
We also add ultraviolet aperture photometry from GALEX5 by us-
ing aperture radii of 3′′ in both far-ultraviolet (FUV) and near-ultraviolet
(NUV) passbands. This photometry was not used to derive the star clus-
ter parameters, but only for the qualitative conﬁrmation of the results in
the case of young clusters, as ultraviolet magnitudes fade very quickly with
age, becoming too faint at the distance of M33 after ≳100 Myr. Also, the
very wide Point Spread Function (PSF) of the GALEX telescope makes the
accurate derivation of UV colors impossible for all clusters, but only for the
few relatively isolated ones (at least at a distance of two aperture radii from
any other UV-emission in the worst cases).
Fig. 3.15 presents the multi-passband photometric data in diﬀerent color-
color diagrams in optical cases (UBV RI and u∗g′r′i′z′). Fig. 3.16 shows
the clusters in the GALEX photometry (top panels) only for objects undis-
turbed by close neighboring UV emission, and in deep 2MASS 6X photo-
metry (bottom panels). The clusters are shown with SSP models (solid
lines) and also with a grid of artiﬁcial star cluster models which take the
stochastic dispersion of their colors into account, as described in Section 1.4.
Both SSP and stochastic model grid are shown with the same metallicity,
[M/H] = −0.4.
Although GALEX photometry is inaccurate for most of the 910 objects,
because of the presence of possible UV emitting neighboring objects, we
5GALEX: https://archive.stsci.edu/prepds/galex_atlas/index.html
86
Fig. 3.17. Top panels: BV Hα multi-passband pictures of star clusters still embedded
in HII zones. Bottom panels: same clusters as in top panels but shown in the GALEX
FUV (blue) and NUV (red) passbands. In each panel, green circles are drawn around
the clusters with a radius of 2′′.
Fig. 3.18. Same as in Fig. 3.17 but for star clusters bright in ultraviolet.
Fig. 3.19. Same as in Fig. 3.17 but for star clusters faint in ultraviolet.
87
Fig. 3.20. Same as in Fig. 3.17 but for globular-like star clusters.
Fig. 3.21. Same as in Fig. 3.17 but for highly-probable stars.
used the FUV photometry as a criterion for the qualitative evaluation of
the UV emission strength. Objects are said to be bright in UV when their
aperture photometry within an aperture radius of 3′′ is brighter than 20 mag,
and faint in UV when it is fainter than this limit.
In Figs. 3.15 and 3.16, the clusters are color-coded following their types:
bright in UV (blue), faint in UV (cyan), embedded or close to HII zones
(white), and globular-like clusters (red). Clusters are classiﬁed as globular-
like following their visual conﬁrmation using HST images (Sarajedini et al.
1998; Chandar et al. 1999a; San Roman et al. 2009). Also, the deep Subaru
images were used to reject 95 high-probable stars from our star cluster
sample.
These stellar objects are marked as green star symbols in the
color-color diagrams of Figs. 3.15 and 3.16.
We also used deep BV RIHα optical images from the Subaru 8 m tele-
88
scope and 24 µm image from the Spitzer6 telescope.
We created multi-
passband images for each cluster in our catalog that were used to visually
conﬁrm the results of our method of star cluster parameter derivation. In
Fig. 3.17, we show ﬁve clusters still embedded in HII zones by use of BV Hα
as well as GALEX (FUV and NUV) sky images. In Figs. 3.18 and 3.19 a
few clusters bright in UV (Fig. 3.18) and faint in UV (Fig. 3.19) are shown.
In Fig. 3.20 a few globular-like clusters are shown, and in Fig. 3.21 a few
objects from the sample that are very likely stars are shown.
After the rejection of the 95 stars from the 910 objects sample as well
as a few clusters with incomplete photometry, 747 clusters remain to be
studied.
3.3.3
Artiﬁcial tests
The ability of the method to derive star cluster parameters has already
been evaluated in Sections 2.3, 2.4, 2.5, and 2.6. Here we are interested
in seeing for which conditions the method would be sensitive enough to
detect a change in slope in the number of clusters per age bin distribution
(hereafter referred to as diﬀerential age distribution) of the cluster sample
such as shown by the solid line in Fig. 3.22 (d). Indeed, a two-slope proﬁle
in the diﬀerential age distribution could be interpreted as a decrease in the
number of clusters due to an evolutionary fading of the cluster magnitudes
(ﬁrst slope) and a decrease in the number of clusters due to their disruption
(second slope), as is discussed in greater details in Section 3.3.4. Here, the
objective is to model an artiﬁcial star cluster population with such a two-
slope proﬁle in the true diﬀerential age distribution and to see whether the
derived diﬀerential age distribution reproduces this proﬁle depending on
which photometric system we use.
We generated a sample of 10 000 artiﬁcial star clusters. The diﬀerential
age distribution of the artiﬁcial clusters was chosen to mimic a two-slope
proﬁle similar to that described in Vansevičius et al. (2009) for M31 star
clusters (see their Fig. 5a, reproduced in our Fig. 3.22 (d) in solid line).
For simplicity, the mass of the clusters was ﬁxed to log10(M/M⊙) = 4, a
typical value for the clusters observed in M33. The extinction was randomly
6Spitzer: http://ssc.spitzer.caltech.edu/spitzerdataarchives/
89
7
8
9
10
log10(t=yr) derived
a)
1
2
3
N
b)
0.2
0.4
0.6
0.8
N
c)
−3
−1
1
3
log10(dN=dt) [yr¡1 ]
d)
7
8
9
10
log10(t=yr) derived
e)
1
2
3
N
f)
0.2
0.4
0.6
0.8
N
g)
−3
−1
1
log10(dN=dt) [yr¡1 ]
h)
7
8
9
10
log10(t=yr) true
7
8
9
10
log10(t=yr) derived
i)
3
4
5
log10(M=M ¯) derived
1
2
3
N
j)
7
8
9
10
log10(t=yr)
0.2
0.4
0.6
0.8
N
k)
7
8
9
10
log10(t=yr)
−3
−1
1
log10(dN=dt) [yr¡1 ]
l)
Fig. 3.22. Artiﬁcial tests for 10 000 clusters with true age and metallicity following a
deﬁned age-metallicity relation (see text), and with a true mass ﬁxed to log10(M/M⊙) =
4. The ﬁrst column of panels displays the age derived vs the true age, the second column
shows the derived mass distribution, the third column shows the true age distribution
(solid line histogram) and derived age distribution (dashed line histogram), and the last
column shows the diﬀerential true age distribution (solid line), which is composed of a
two-slope proﬁle, and the derived diﬀerential age distribution (dashed line). The ﬁrst
row of panels shows results obtained using the UBV RI photometric system, the second
row shows the results obtained using the UBV RI + JHK system and the last row
shows the results obtained with the GALEX + UBV RI system. Here the metallicity of
the model grid is ﬁxed to [M/H] = −0.4.
generated uniformly in the range E(B −V ) = 0 to 1.
For the cluster metallicities, we use a very simple age-metallicity rela-
tion: for the youngest clusters the metallicity is supersolar, [M/H] = 0.2,
and for the oldest clusters the metallicity is very low, [M/H] = −1.8.
The age-metallicity relation is linear between these values, in the age
(log10(t/yr))–metallicity ([M/H]) space. The metallicity of clusters is gen-
erated with a Gaussian dispersion of 0.4 dex standard deviation around this
age-metallicity relation.
The ﬁrst test, presented in Fig. 3.22, has been performed using a cluster
model grid with the metallicity ﬁxed to [M/H] = −0.4 to show the possible
biases that occur when metallicity is not a free parameter. The test is per-
90
7
8
9
10
log10(t=yr) derived
a)
1
2
3
N
b)
0.2
0.4
0.6
0.8
N
c)
−3
−1
1
3
log10(dN=dt) [yr¡1 ]
d)
7
8
9
10
log10(t=yr) derived
e)
1
2
3
N
f)
0.2
0.4
0.6
0.8
N
g)
−3
−1
1
log10(dN=dt) [yr¡1 ]
h)
7
8
9
10
log10(t=yr) true
7
8
9
10
log10(t=yr) derived
i)
3
4
5
log10(M=M ¯) derived
1
2
3
N
j)
7
8
9
10
log10(t=yr)
0.2
0.4
0.6
0.8
N
k)
7
8
9
10
log10(t=yr)
−3
−1
1
log10(dN=dt) [yr¡1 ]
l)
Fig. 3.23. Same as in Fig. 3.22, but for clusters which have derived ages larger than
log10(t/yr) = 9 when using a ﬁxed [M/H] = −0.4 metallicity, we re-derive a solution
leaving the metallicity free to vary in the range [+0.2, −2.2].
7
8
9
10
log10(t=yr) derived
a)
1
2
3
N
b)
0.2
0.4
0.6
0.8
N
c)
−3
−1
1
3
log10(dN=dt) [yr¡1 ]
d)
7
8
9
10
log10(t=yr) derived
e)
1
2
3
N
f)
0.2
0.4
0.6
0.8
N
g)
−3
−1
1
log10(dN=dt) [yr¡1 ]
h)
7
8
9
10
log10(t=yr) true
7
8
9
10
log10(t=yr) derived
i)
3
4
5
log10(M=M ¯) derived
1
2
3
N
j)
7
8
9
10
log10(t=yr)
0.2
0.4
0.6
0.8
N
k)
7
8
9
10
log10(t=yr)
−3
−1
1
log10(dN=dt) [yr¡1 ]
l)
Fig. 3.24. Same as in Fig. 3.22, but the metallicity of the model grid is left free over
the whole age range.
91
formed for three combinations of photometric systems: optical (UBV RI),
optical with near-infrared (UBV RI + JHK) and ultraviolet with optical
(GALEX + UBV RI). The UBV RI system is used as a reference for the
mass derivation, so it has been used in magnitudes in Eq. 2.1. For the other
passbands, we have used colors instead, FUV-NUV for the GALEX pass-
bands and J −H, J −K, and H −K for the 2MASS ones. This allows us to
combine diﬀerent catalogs of clusters built using slightly diﬀerent aperture
sizes: we use the magnitudes for one catalog, and the colors for the others.
However, it is important that for each cluster at least one magnitude should
be given, not just colors, so that the mass of the clusters could be estimated
reliably by the method.
We added photometric uncertainties as a Gaussian noise with standard
deviations of 0.05 mag for each UBV RI photometric passbands, 0.1 mag for
JHK, and 0.15 mag for GALEX FUV and NUV.
In Fig. 3.22 we see how the derived cluster age (panel a) and mass (panel
b) are distributed versus the true values (indicated by dashed lines). Pan-
els (c) and (d) concentrate on the age derivation, and show that the peak
in the true age distribution (indicated by thin lines in panels c and d) is
already found using optical data only. The true peak in age, situated at
log10(t/yr) ∼8.3 in panel (c) (solid line histogram) and corresponding to
a change in slope at log10(t/yr) = 8.5 in panel (d) (solid line), is correctly
derived as maximum in panel (c) (dashed line histogram) and change of
slope in panel (d) (dashed line). However, the apparent good match be-
tween the true age and the derived age distributions in panels (c) and (d)
can be rather misleading when using UBV RI photometry alone. Indeed
the direct comparison of the true and derived ages of the individual clusters
in panel (a) shows that the agreement is far from being evident, especially
at old ages, where the true metallicity of artiﬁcial clusters and the ﬁxed one
of the model grid ([M/H] = −0.4) deviate most. As a natural consequence,
most of the clusters with true age above log10(t/yr) = 9.5 have age under-
estimated. Also, the presence of the natural age-extinction degeneracy in
the optical UBV RI case, already discussed in Sections 2.3, 2.4, and 2.5,
produces the streaks developing perpendicularly to the left and to the right
of the diagonal identity dashed line, in Fig. 3.22 (a). The situation is less ex-
92
treme, but still strongly aﬀected by these degeneracies when we add JHK
passbands to UBV RI ones (second row of panels). When we use GALEX
with UBV RI passbands (third row of panels), the age-extinction degen-
eracy disappears, but the deviation from the identity line occurs because
of the strong sensitivity of the ultraviolet to metallicity. Bianchi (2011)
indeed shows by use of integrated spectra of SSP models that it is in the
ultraviolet spectral region that the spectra are most aﬀected by a change
in metallicity.
We performed a second test, ﬁxing the metallicity to [M/H] = −0.4 for
all clusters, and then, only for clusters which have derived age larger than
log10(t/yr) = 9, we re-derive a solution leaving the metallicity free to vary in
the range [+0.2, −2.2]. Indeed, one notices in the ﬁrst test that the situation
was most complicated for clusters with true age above 1 Gyr. The results,
shown in Fig. 3.23, still suﬀer from strong age-extinction degeneracy in the
case of UBV RI passbands only (ﬁrst row of panels). The inclusion of near-
infrared photometry improves much the derivation as the streaks developing
perpendicularly to the identity line in Fig. 3.23 (e) are strongly reduced. In
this case, the match between the true and derived age distributions in panels
(g) and (h) is much more secure for all age ranges. When using GALEX
with UBV RI (third row of panels), a gap is visible in panel (i) due to the
strong sensitivity of the ultraviolet ﬂux to metallicity. In this case, strong
biases are still present in the age distribution (Fig. 3.23k and Fig. 3.23l).
A third test was performed in which the metallicity of the model grid was
left free in the whole age range, and the results are presented in Fig. 3.24.
Here we see that the use of optical passbands only (ﬁrst row of panels) or
even optical with near-infrared (second row) can lead to strong biases as
these photometric systems are not sensitive enough to discriminate between
models of diﬀerent metallicities (see also Sections 2.4 and 2.5 for the sensitiv-
ity of the derived parameters on the metallicity, as well as for the derivation
of the metallicity parameter). As a consequence, age distributions (panels
c and d for the UBV RI case, panels g and h for the UBV RI + JHK case)
are strongly aﬀected. Only ultraviolet associated with optical data pass-
bands are able to break the age-extinction degeneracies when the metallicity
is left free, as shown in last row of panels. As a consequence, the derivation
93
of the correct two-slopes proﬁle in the diﬀerential age distribution is best
done using GALEX + UBV RI when metallicity is left free, see Fig. 3.24l).
3.3.4
The derived physical parameters of the M33 star
clusters
We applied the method of derivation of physical parameters to the sam-
ple of 747 M33 clusters using the optical UBV RI and near-infrared JHK
passbands. We ﬁrst ﬁx the metallicity to [M/H] = −0.4 for all clusters, and
then, only for clusters which have derived age larger than log10(t/yr) = 9,
we re-derive a solution leaving the metallicity free to vary in the range
[+0.2, −2.2], as it was shown to be the best choice for this passband com-
bination in previous section.
As it has been done for artiﬁcial tests, we used the UBV RI system
as a reference for the mass derivation, so it has been used in magnitudes
in Eq. 2.1.
For the other passbands used, u∗g′r′i′z′ and JHK, we have
used colors instead, to avoid problems of diﬀerent apertures in the diﬀerent
catalogs used. The colors used were u∗−g′, g′ −r′, g′ −i′, r′ −i′, and i′ −z′
for the CFHT passbands, and J −H, J −K, and H −K for the 2MASS
passbands.
We used the extinction law of Gordon et al. (2003) derived for the LMC,
assuming that for a similar metallic content the M33 galaxy would have a
similar extinction law. The minimum extinction of clusters has been set
to E(B −V ) = 0.04 mag, the value of the foreground extinction in the
direction of M33 estimated from the Schlegel et al. (1998) extinction maps.
The results for the age and mass obtained here are compared in Fig. 3.25
with those of 160 San Roman et al. (2009), obtained by isochrone ﬁtting
on HST-resolved color-magnitude diagrams. In the case of the San Roman
et al. (2009), cluster ages are enclosed in a much narrower range, mainly
between 50 Myr and 1 Gyr. Although our age distribution is wider than in
their case, a satisfactory agreement is found between both sets of results,
as well as for the mass parameter.
Globular-like clusters (red circles, visually conﬁrmed as globular clus-
ters on HST images) are found to be very old in our case, and more mas-
sive. San Roman et al. (2009) noted that the lack of clusters with ages
94
7
8
9
10
log10(t/yr) this work
7
8
9
10
log10(t/yr) SR09
a)
2
3
4
5
6
log10(M/M ⊙) this work
2
3
4
5
6
log10(M/M ⊙) SR09
b)
7
8
9
10
log10(t/yr) this work
2
1
0
1
2
log10(t/yr) SR09−this work
c)
2
3
4
5
6
log10(M/M ⊙) this work
2
1
0
1
2
log10(M/M ⊙) SR09−this work
d)
Fig. 3.25. Comparison of the age and mass derived for clusters common to San Roman
et al. (2009). The ﬁrst row shows the comparison of the parameters of these studies
vs the present work, and the second row shows the diﬀerence between the parameters
derived in their studies and in this work vs the parameters derived in this work. The
color-coding of clusters is the same as deﬁned in Fig. 3.15.
older than ∼1 Gyr in their catalog is linked to the fact that their resolved
color-magnitude diagrams are generally not deep enough to detect the main
sequence turn-oﬀof the clusters older than this age. In Fig. 3.25, the two
oldest and most massive clusters (according to our derived age and mass)
are globular clusters known as CBF85-U137 and MKKSS12. For CBF85-
U137, we ﬁnd log10(t/yr) = 10.05 and log10(M/M⊙) = 5.25, while San
Roman et al. (2009) give log10(t/yr) = 8.8 and log10(M/M⊙) = 4.4. Chan-
dar et al. (2002) give log10(t/yr) = 10.08 (12 Gyr in their table 5) using
the spectroscopic line index models of Worthey (1994). For MKKSS12, we
95
7
8
9
10
log10(t/yr) this work
7
8
9
10
log10(t/yr) SM10
a)
2
3
4
5
6
log10(M/M ⊙) this work
2
3
4
5
6
log10(M/M ⊙) SM10
b)
7
8
9
10
log10(t/yr) this work
2
1
0
1
2
log10(t/yr) SM10−this work
c)
2
3
4
5
6
log10(M/M ⊙) this work
2
1
0
1
2
log10(M/M ⊙) SM10−this work
d)
Fig. 3.26. Comparison of the age and mass derived for clusters common with Saraje-
dini & Mancone (2007) (”SM10” because revised catalog in 2010). The ﬁrst row shows
the comparison of the parameters of these studies vs the present work, and the second
row shows the diﬀerence of the parameters derived in their studies and this work vs the
parameters derived in this work. The color-coding of clusters is the same as deﬁned in
Fig. 3.15.
ﬁnd log10(t/yr) = 10.0 and log10(M/M⊙) = 5.65, while San Roman et al.
(2009) give log10(t/yr) = 8.6 and log10(M/M⊙) = 4.54. Chandar et al.
(2002) give log10(t/yr) = 9.4 using SSP models, and Ma et al. (2004) give
log10(t/yr) = 9.63 and log10(M/M⊙) = 5.47 using their BATC spectropho-
tometric system composed of 13 narrow passbands, also compared to SSP
models.
For young clusters, the age given by San Roman et al. (2009) is often
larger than our values. In Fig. 3.25 (a,c) we note that the two white circles,
96
which are for the clusters still within HII zones and so very young, are also
seen as older in San Roman et al. (2009) than in our study. Also, many
clusters that are bright in UV (blue circles) are also older in San Roman
et al. (2009) than in our case. However, UV brightness fades very quickly,
becoming faint at the distance of M33 after ≳100 Myr, making it unlikely
that the age of these clusters is older.
Fig. 3.26 compares the results found for the clusters common with the
merged catalog of Sarajedini & Mancone (2007) (referred to as “SM10” in
the ﬁgure because revised in 2010); the agreement for both age and mass
parameters is less good. One has to keep in mind that the Sarajedini &
Mancone (2007) catalog contains results from very diﬀerent studies. Many
of these results have been obtained using SSP models on integrated un-
resolved ground-based photometry using optical colors only, a technique
that has been shown to be strongly biased by the stochasticity problem and
the presence of strong degeneracies (see e.g., Fouesneau & Lançon 2010,
Sections 1.1 and 1.2).
Fouesneau & Lançon (2010) created a sample of
stochastically generated artiﬁcial star clusters and tried to derive their age
using SSP models. Their results, shown in the bottom left panel of their
Fig. 3 are similar to the values given in our Fig. 3.26 (a). The concentra-
tions of solution at ages log10(t/yr) ∼7 and log10(t/yr) ∼9 for Sarajedini
& Mancone (2007) seem to be artifacts due to the SSP method, as is the
case for the SSP derived ages in Fig. 3 of Fouesneau & Lançon (2010).
Popescu et al. (2012) show the same features, this time for real clusters.
They derived the age of LMC star clusters using the stochastic method and
compared these values to the ages derived by Hunter et al. (2003) using the
SSP method. The comparison, shown in Fig. 8 of Popescu et al. (2012)
(the order of the x- and y-axes is ﬂipped compared to our ﬁgure), shows
similar features to the Fouesneau & Lançon (2010) study and to this work:
the deviations from the identity line are attributed to artefacts of the SSP
method of parameter derivation.
Fig. 3.27 presents the results for the star cluster sample studied. As ex-
pected, the mass versus age distribution in Fig. 3.27 (a) shows a diﬀerent
typical age for the diﬀerent classes of clusters. The youngest ones are em-
bedded or close to HII zones (white circles), then comes the clusters bright
97
in the UV (blue circles) then the faint in the UV (cyan circles), and, ﬁnally,
the globular-like clusters (red circles). The solid line shows the 50% com-
pleteness line evaluated in Fan & de Grijs (2014) for their cluster sample.
As our merged cluster sample also contains the HST detected objects from
San Roman et al. (2009), some clusters may be found well below this limit.
For M33, U et al. (2009) derived the extinction of 22 supergiant stars,
which resulted in an extinction distribution centered on E(B−V ) = 0.1 mag.
U et al. (2009) also used the data of Rosolowsky & Simon (2008) to derive
the E(B −V ) values for 58 HII regions, and show in their Fig. 9 that the
extinction can be expected to be E(B −V ) ≲0.3 mag for those regions
(except for 3 objects), with an average of E(B −V ) ∼0.11 mag.
In Fig. 3.27 (f) is shown the extinction of all clusters depending on their
deprojected galactocentric distance (assuming that all clusters are in the
disk, which is incorrect for globular-like clusters). The global median ex-
tinction is 0.16 mag. The extinction that we found is generally higher for
young clusters than for old ones, as shown in Fig. 3.27 (b).
Indeed, the
majority of clusters still embedded or close to HII zones (white circles)
are found more extincted with a median of 0.34 mag. The clusters bright
in UV (blue circles) have a median extinction of 0.17 mag, while the clus-
ters faint in UV (cyan circles) have a lower median extinction of 0.14 mag.
The globular-like clusters (red circles) have the smallest median extinction,
0.09 mag.
Fig. 3.28 describes the age and mass distributions (panels a and b), and
the diﬀerential age and mass distributions (panels c and d). We see that the
diﬀerential age distribution is composed of a two-slope proﬁle. Boutloukos
& Lamers (2003) and Lamers et al. (2005) interpreted the ﬁrst slope as a
natural magnitude fading due to stellar evolution, and the second slope as
due to cluster disruption mechanisms such as the galaxy tidal ﬁeld eﬀect or
encounters with giant molecular clouds. Hence we see here that the cluster
sample is dominated by the magnitude fading until log10(t/yr) ∼8.5 and
that after the cluster disruption phase takes over.
This typical lifetime
scale is comparable to the one derived for the star cluster population in the
south-west ﬁeld of the M31 galaxy by Vansevičius et al. (2009) using a star
cluster sample photometry from Narbutis et al. (2008).
98
7
8
9
10
log10(t/yr)
2
3
4
5
6
log10(M/M ⊙)
a)
7
8
9
10
log10(t/yr)
0
-0.5
-1
-1.5
-2
[M/H]
b)
7
8
9
10
log10(t/yr)
0.0
0.2
0.4
0.6
0.8
1.0
E(B−V)
c)
2
3
4
5
6
log10(M/M ⊙)
0.0
0.2
0.4
0.6
0.8
1.0
E(B−V)
d)
0.0
0.2
0.4
0.6
0.8
1.0
E(B−V)
0
40
80
120
N
e)
0
10
20
30
40
deprojected distance [arcmin]
0.0
0.2
0.4
0.6
0.8
1.0
E(B−V)
f)
Fig. 3.27. Results derived for the 747 clusters studied for the mass vs age (panel a),
metallicity vs age (panel b), extinction vs age (panel c), extinction vs mass (panel d), the
extinction histogram (panel e), and the extinction versus the deprojected galactocentric
distance (panel f) of the cluster population.
The solid line in panel (a) shows the
photometric 50% completeness limit estimated in Fan & de Grijs (2014) for their optical
ground-based cluster catalog. As emphasized in the text, the metallicity of the clusters,
shown in panel (b), has been ﬁxed to [M/H] = −0.4 when the clusters derived age
using that metallicity is lower than 1 Gyr, and for clusters with older derived age, a new
solution is derived with free metallicity in the range [+0.2, −2.2]. The color-coding of
clusters is the same as deﬁned in Fig. 3.15.
99
7
8
9
10
log10(t=yr)
0
40
80
120
N
a)
2
3
4
5
6
log10(M=M ¯)
0
40
80
120
160
N
b)
7
8
9
10
log10(t=yr)
−3
−1
1
3
log10(dN=dt) [yr¡1 ]
c)
2
3
4
5
6
log10(M=M ¯)
−8
−6
−4
log10(dN=dM=Ntot) [M ¯
¡1 ]
d)
Fig. 3.28. Top row: age (panel a) and mass (panel b) distributions derived for the
M33 star cluster sample. Bottom row: diﬀerential age (panel c) and mass (panel d)
distributions. In panel (c), the solid line and the dashed line are respectively the cluster
evolutionary fading rate and the cluster disruption rate, both taken from the case of M31
(Vansevičius et al. 2009) and shifted vertically here for comparison. The dark histogram
in panel (b) and the black circles in panel (d) represent a subsample of clusters with ages
between 100 Myr and 3 Gyr. The dashed line in panel (d) represents the cluster mass
function that follows a Schechter (1976) function with β = 2 and M∗= 2 × 105M⊙.
100
Following Gieles (2009), we compare the cluster diﬀerential mass distri-
bution to the Schechter (1976) distribution function, deﬁned as
dN/dM = A × M−β × exp(−M/M∗)
(3.1)
where the constant A scales with the cluster formation rate, β is the power-
law index of the mass function and M∗stands for the characteristic mass
after which the exponent term decreases strongly.
As was found for most spiral galaxies (see, e.g., Larsen 2009; Portegies
Zwart et al. 2010), the derived mass function of the star cluster sample fol-
lows the Eq. 3.1 distribution function with β = 2 and M∗= 2×105M⊙. We
adapted the scaling constant A to scale it to the cluster mass distribution,
shown in Fig. 3.28 (d).
101
102
Conclusions
In this work, we aimed to tackle the two major problems faced when de-
riving the physical parameters (age, mass, extinction, and metallicity) of
unresolved star clusters, that are the problems of the degeneracy between
the star cluster parameters, and the stochastic dispersion of observed cluster
colors due to the stochastic sampling of massive stars.
In Chapter 1, the problems of degeneracy and stochasticity have been
introduced for unresolved star clusters with integrated broad-band photo-
metry. It has been shown that the Simple Stellar Population models are
unﬁt to derive the cluster parameters. Then the stellar mass random sam-
pling method that allows us to model the stochasticity in star clusters has
been presented, as well as the model grid built for all physical parameters
of star clusters.
In Chapter 2, the method to derive the star cluster physical parameters
has been developed taking into account the stochasticity problem.
The
method has been tested on several artiﬁcial cluster samples in the cases
where the extinction and metallicity are known or unknown, to show the
degeneracies linked to these parameters. By use of diﬀerent photometric
system combinations, UBV RI, UBV RI + JHK, GALEX+UBV RI, and
WFC3, it has been demonstrated that the ultraviolet combined with optical
is best suited for the break of degeneracies between clusters parameters. The
impact of photometric errors has also been studied for the particular case
of the WFC3 photometric system.
In Chapter 3, the method of cluster parameter derivation has been ap-
plied on real star cluster samples from two major Local Group galaxies,
M31 and M33. For M31 clusters, the age-extinction degeneracy has been
explored using a star cluster sample of Vansevičius et al. (2009) based
on ground-based UBV RI photometry, and the age-metallicity degeneracy
has been explored using a star cluster sample of PHAT survey (Johnson
et al. 2012), observed in the WFC3 photometric system onboard the Hub-
ble Space Telescope. In the latter case we derived the cluster parameters,
including the metallicity, and hence showed the metallicity eﬀects on the
103
parameter derivation accuracy. For the clusters in common to the Caldwell
et al. (2011) spectroscopic study, we compared the metallicity with their
values and found and overall agreement. This demonstrated by use of the
sample of real star clusters that the WFC3 photometric system is suitable
to evaluate the star cluster parameters when the metallicity is unknown,
and evaluates the metallicity when the signal-to-noise is high enough.
Finally, we studied the star cluster system of the M33 galaxy, using the
most recent optical broad-band photometry catalogs, and supplemented
near-infrared measurements using deep 2MASS images. We presented the
derivation of the age, mass, and extinction of the clusters for a metallicity
ﬁxed to [M/H] = −0.4 (LMC-like), and, in the case when the age derived is
larger than 1 Gyr, a new solution was derived using free metallicity in the
range [+0.2, −2.2].
We ensured, by use of artiﬁcial clusters, that the star cluster physi-
cal parameter derivation method can reproduce correctly a given two-slope
proﬁle in the diﬀerential age distribution, testing it for diﬀerent photome-
tric systems: optical alone (UBV RI), optical combined with near-infrared
(UBV RI + JHK), and ultraviolet with optical (GALEX + UBV RI). We
showed that the optical with near-infrared case is suitable for the correct
derivation of the two-slope proﬁle and used it for the M33 star cluster sys-
tem.
A two-slope proﬁle of diﬀerential age distribution found for the M33
star cluster system has been interpreted as: the typical lifetime before dis-
ruption of star clusters in M33 is found to be ∼300 Myr, comparable to
what is found for M31 star clusters. We showed that the diﬀerential mass
distribution of clusters is consistent with a Schechter (1976) function with
a power-law index of β = 2 and a characteristic mass of M∗= 2 × 105M⊙.
To conclude, we have demonstrated in this thesis, by use of artiﬁcial
tests as well as real star clusters, that stochastic modeling of star clusters
is best ﬁtted to derive their parameters, as well as to derive the essential
properties of star cluster populations in other galaxies.
104
References
Anders P., Bissantz N., Fritze-v. Alvensleben U., et al. 2004, MNRAS, 347, 196
Andrae R. 2010, ArXiv e-prints
Barbaro C., Bertelli C. 1977, A&A, 54, 243
Beerman L.C., Johnson L.C., Fouesneau M., et al. 2012, ApJ, 760, 104
Bertelli G., Bressan A., Chiosi C., et al. 1994, A&AS, 106, 275
Bianchi L. 2011, Ap&SS, 335, 51
Boutloukos S.G., Lamers H.J.G.L.M. 2003, MNRAS, 338, 717
Bridžius A., Narbutis D., Stonkutė R., et al. 2008, Baltic Astronomy, 17, 337
Caldwell N., Harding P., Morrison H., et al. 2009, AJ, 137, 94
Caldwell N., Schiavon R., Morrison H., et al. 2011, AJ, 141, 61
Cardelli J.A., Clayton G.C., Mathis J.S. 1989, ApJ, 345, 245
Cerviño M., Luridiana V. 2004, A&A, 413, 145
—. 2006, A&A, 451, 475
Cerviño M., Valls-Gabaud D., Luridiana V., et al. 2002, A&A, 381, 51
Chandar R., Bianchi L., Ford H.C. 1999a, ApJS, 122, 431
—. 1999b, ApJ, 517, 668
—. 2001, A&A, 366, 498
Chandar R., Bianchi L., Ford H.C., et al. 1999c, PASP, 111, 794
—. 2002, ApJ, 564, 712
Chiosi C., Bertelli G., Bressan A. 1988, A&A, 196, 84
Christian C.A., Schommer R.A. 1982, ApJS, 49, 405
—. 1988, AJ, 95, 704
da Silva R.L., Fumagalli M., Krumholz M. 2012, ApJ, 745, 145
Dalcanton J.J., Williams B.F., Lang D., et al. 2012, ApJS, 200, 18
105
de Meulenaer P., Narbutis D., Mineikis T., et al. 2013, A&A, 550, A20, Paper I
—. 2014a, A&A, 569, A4, Paper II
—. 2014b, Baltic Astronomy, 23, 199
—. 2015a, A&A, 574, A66, Paper III
—. 2015b, ArXiv e-prints, Paper IV
Dempster A.P., Laird N.M., Rubin D.B. 1977, Journal of the Royal Statistical
Society, Series B, 39, 1
Deveikis V., Narbutis D., Stonkutė R., et al. 2008, Baltic Astronomy, 17, 351
Fan Z., de Grijs R. 2014, ApJS, 211, 22
Fioc M., Rocca-Volmerange B. 1997, A&A, 326, 950
—. 1999, ArXiv Astrophysics e-prints
Fouesneau M., Johnson L.C., Weisz D.R., et al. 2014, ApJ, 786, 117
Fouesneau M., Lançon A. 2010, A&A, 521, A22
Galleti S., Bellazzini M., Ferraro F.R. 2004, A&A, 423, 925
Gieles M. 2009, MNRAS, 394, 2113
Girardi L., Bertelli G. 1998, MNRAS, 300, 533
Girardi L., Williams B.F., Gilbert K.M., et al. 2010, ApJ, 724, 1030
Gordon K.D., Clayton G.C., Misselt K.A., et al. 2003, ApJ, 594, 279
Groenewegen M.A.T., de Jong T. 1993, A&A, 267, 410
Hiltner W.A. 1960, ApJ, 131, 163
Hunter D.A., Elmegreen B.G., Dupuy T.J., et al. 2003, AJ, 126, 1836
Johnson L.C., Seth A.C., Dalcanton J.J., et al. 2012, ApJ, 752, 95
Kaviraj S., Rey S.C., Rich R.M., et al. 2007, MNRAS, 381, L74
Kron G.E., Mayall N.U. 1960, AJ, 65, 581
Kroupa P. 2001, MNRAS, 322, 231
—. 2002, Science, 295, 82
Kroupa P., Weidner C. 2003, ApJ, 598, 1076
106
Kroupa P., Weidner C., Pﬂamm-Altenburg J., et al. 2013, The Stellar and Sub-
Stellar Initial Mass Function of Simple and Composite Populations, 115
Lamers H.J.G.L.M., Gieles M., Portegies Zwart S.F. 2005, A&A, 429, 173
Lançon A., Mouhcine M. 2000, in Massive Stellar Clusters, eds. A. Lançon, C.M.
Boily, vol. 211 of Astronomical Society of the Paciﬁc Conference Series, 34
Larsen S.S. 2009, A&A, 494, 539
Ma J. 2012, AJ, 144, 41
—. 2013, AJ, 145, 88
Ma J., Zhou X., Chen J. 2004, A&A, 413, 563
Marigo P., Girardi L., Bressan A., et al. 2008, A&A, 482, 883
Massey P., Olsen K.A., Hodge P.W., et al. 2006, in American Astronomical Society
Meeting Abstracts, vol. 38 of Bulletin of the American Astronomical Society,
939
McConnachie A.W., Irwin M.J., Ferguson A.M.N., et al. 2005, MNRAS, 356, 979
Melnick J., D’Odorico S. 1978, A&AS, 34, 249
Mochejska B.J., Kaluzny J., Krockenberger M., et al. 1998, Acta Astronomica,
48, 455
Narbutis D., Bridžius A., Stonkutė R., et al. 2007, Baltic Astronomy, 16, 421
Narbutis D., Vansevičius V., Kodaira K., et al. 2008, ApJS, 177, 174
Pedregosa F., Varoquaux G., Gramfort A., et al. 2011, Journal of Machine Learn-
ing Research, 12, 2825
Pﬂamm-Altenburg J., Kroupa P. 2006, MNRAS, 373, 295
Pﬂamm-Altenburg J., Weidner C., Kroupa P. 2007, ApJ, 671, 1550
Popescu B., Hanson M.M. 2010, ApJ, 724, 296
—. 2014, ApJ, 780, 27
Popescu B., Hanson M.M., Elmegreen B.G. 2012, ApJ, 751, 122
Portegies Zwart S.F., McMillan S.L.W., Gieles M. 2010, ARA&A, 48, 431
Regan M.W., Vogel S.N. 1994, ApJ, 434, 536
Rosolowsky E., Simon J.D. 2008, ApJ, 675, 1213
107
Salaris M., Cassisi S. 2006, Evolution of Stars and Stellar Populations
Salpeter E.E. 1955, ApJ, 121, 161
San Roman I., Sarajedini A., Aparicio A. 2010, ApJ, 720, 1674
San Roman I., Sarajedini A., Garnett D.R., et al. 2009, ApJ, 699, 839
Santos Jr. J.F.C., Frogel J.A. 1997, ApJ, 479, 764
Sarajedini A., Barker M.K., Geisler D., et al. 2007, AJ, 133, 290
Sarajedini A., Geisler D., Harding P., et al. 1998, ApJ, 508, L37
Sarajedini A., Geisler D., Schommer R., et al. 2000, AJ, 120, 2437
Sarajedini A., Mancone C.L. 2007, AJ, 134, 447
Schechter P. 1976, ApJ, 203, 297
Schlegel D.J., Finkbeiner D.P., Davis M. 1998, ApJ, 500, 525
Silva-Villa E., Larsen S.S. 2011, A&A, 529, A25
U V., Urbaneja M.A., Kudritzki R.P., et al. 2009, ApJ, 704, 1120
Vansevičius V., Kodaira K., Narbutis D., et al. 2009, ApJ, 703, 1872
Weidner C., Kroupa P., Bonnell I.A.D. 2010, MNRAS, 401, 275
Weidner C., Kroupa P., Pﬂamm-Altenburg J. 2013, MNRAS, 434, 84
Weisz D.R., Fouesneau M., Hogg D.W., et al. 2013, ApJ, 762, 123
Worthey G. 1994, ApJS, 95, 107
Zurita A., Bresolin F. 2012, MNRAS, 427, 1463
108
