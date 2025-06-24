# Untitled

**Keywords:** U BV RI + JHK . . 2.4.3 Addition of ultraviolet passbands: GALEX + U BV RI . . 2.5 Metallicity effects: one-metallicity vs whole metallicity range . . . 2.6 Exploration of the metallicity effects for the WFC3 photometric de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving physical parameters of unresolved star clusters. I. Age, mass, and extinction degeneracies, Astronomy and Astrophysics, 2013, 550, A20 2. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving physical parameters of unresolved star clusters. II. The degeneracies of age, mass, extinction, and metallicity, Astronomy and Astrophysics, 2014, 569, A4 3. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Stochasticity in star clusters: Reduced Random Sampling Method, Baltic Astronomy, 2014, 23, 199 4. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving physical parameters of unresolved star clusters. III. Application on M31 PHAT clusters, Astronomy and Astrophysics, 2015, 574, A66 5. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving physical parameters of unresolved star clusters. IV. The M33 star cluster system, Astronomy and Astrophysics (accepted)

**Abstract:**

Star clusters are important tools to probe the star formation mechanisms and star formation history in their host galaxy. The traditional way to derive the physical parameters of star clusters using integrated broad-band photometry makes use of the Simple Stellar Population models (SSP), which can be considered as oversimplified. Indeed, these models consider that the way stellar masses are created in star clusters is by continuously populating the Initial Mass Function (IMF), which is an idealized view. During the last forty years, observations have shown that the Initial Mass Function should be considered as a probability distribution function, according to which stellar masses are sampled randomly. This has the effect to create different number of massive stars in clusters with the same physical parameters and hence dispersing the colors of clusters. This results in strong biases when trying to derive physical parameters of star clusters using oversimplified SSP models.In this thesis, we develop a method of stellar mass sampling which takes into account the stochasticity due to the fact that the IMF is a probability distribution function, which allows us to reproduce the dispersion of star cluster integrated colours. A model grid is built to reproduce all possible choices of physical parameters (age, mass, extinction, and metallicity). We also built a method to derive these parameters, comparing the integrated colors of observed clusters to the ones of our model grid. The method is tested on artificial models, to derive its accuracy. We show that the derivation of parameters, such as metallicity, is possible under good photometric conditions that we quantify. We also compare the derivation of star cluster parameters using different photometric systems, and show that the photometric systems containing ultraviolet passbands are privileged for a best determination of parameters such as age or metallicity.We apply the method on different star cluster catalogs of the two major Local Group galaxies: M31 and M33. For a M31 star cluster catalog with Hubble Space Telescope (HST) broad-band photometry, we show in the case of bright clusters that the metallicity derivation is consistent with 2.4.

##  Acknowledgments

A PhD thesis is rarely the fruit of the work of a single person, but it includes the contribution of many people. Here I would like to express my gratitude to these many people who helped me in so many ways before and during this thesis. I thank very much Dominique Lambert and Gregor Rauw for supporting me during the search of this doctoral position, and the Dean of Vilnius University Physics Faculty for welcoming and helping me efficiently to enter in the Astronomical Observatory.

I thank colleagues from the Astronomical Observatory for their kind support throughout these four years: Jokubas Sūdžius, Julius Sperauskas, Stanislava Bartašiutė, Arūnas Kučinskas, Audrius Bridžius, Viktoras Deveikis, Saulius Raudeliūnas, Kastytis Zubovas, as well as students Kostas Sabulis and Rokas Naujalis. I also enjoyed fruitful scientific interactions with Nate Bastian, Mark Gieles, Pavel Kroupa, Leo Girardi. I also wish to thank warmly my colleagues Donatas Narbutis and Tadas Mineikis; the advices and precious help that they constantly brought me made this doctoral study a pleasant working time. I should particularly thank Tadas for dedicating so much time to help me when I was struggling with details of the lithuanian language and institutions.

I am indebted to my supervisor Vladas Vansevičius for his teaching, his constant support, and his patience, as it was not easy to have a foreigner student. His wide and deep view in science inspired me in many ways during the thesis, and will certainly continue to have a great impact on the rest of my scientific career.

Merci à toute ma famille pour l'affection et les encouragements que vous m'avez donnés au jour le jour. Merci spécialement à Papa pour son enthousiasme formidable, et Maman pour sa tendresse, vous m'avez tout donné.

Dėkoju savo žmoną, Eglė, už nuolatinį palaikimą ir meilę, ir savo dukrą, Liucija, už sitą nuolatinį džiaugsmą tave laikyti rankose.

"Ce que Dieu a caché aux sages et aux savants, Il l'a révélé aux pauvres et aux tous petits." (Mt 11,25)

##  Introduction Motivation

Star clusters are considered to be the building bricks of galaxies in the sense that most of their stars are believed to be born within star clusters. As a consequence, their study allows a better understanding of the history of the star formation in their host galaxy. They could also be used as constraints for galaxy formation models.

The aim of this work is to help solving two major problems faced by scientists in the attempt to recover the physical parameters of star clusters (age, mass, extinction, and metallicity), especially when they are observed in other galaxies, such as the Local Group Andromeda (M31) and Triangulum (M33) galaxies, with integrated broad-band photometry. The first issue comes from the fact that, in integrated broad-band photometry, clusters with different parameters may have similar integrated colors, an effect referred to as parameter degeneracy.

The second reason preventing accurate derivation of cluster parameters is due to the probabilistic (stochastic) sampling of star masses in star clusters. The stochastic sampling of star masses causes the fluctuation of the number of bright stars for clusters with the same age, mass, extinction, and metallicity, and hence results in different integrated luminosities and colors for clusters. When trying to derive the cluster parameters, this effect, stronger in the case of young and low-mass clusters, introduces very often strong biases on the cluster parameters, that might be far larger than the ones due to photometric uncertainties.

The traditional way to derive the physical parameters of star clusters using integrated broad-band photometry makes use of the Simple Stellar Population models (SSP), which consider that the way stellar masses are created in star clusters is by continuously populating the Initial Mass Function (IMF). This means that these models are oversimplified because they do not take into account the stochastic sampling of star masses happening during the birth of clusters. When modeling the stochastic sampling of star masses in clusters, the physical parameters of the clusters are much better derived than by use of the SSP models, because modeling the stochastic sampling allows a better reproduction of the integrated color distributions of star clusters. Hence, the derivation of star cluster parameters using SSP models should be abandoned in favor of the more realistic modeling of stochastically sampled star clusters. This thesis is motivated by the need to derive as best as possible the parameters of many star clusters and use efficiently the ever growing highquality amount of observations gathered using ground based or space telescopes. The accuracy of our parameter derivation method has been evaluated using artificial star clusters in different photometric systems. We applied the method to derive the physical parameters of populations of star clusters from the M31 and M33 galaxies.

##  Aims of the study

Study the influence of the stochasticity effects on the accuracy of star cluster parameters (age, mass, extinction, and metallicity) derivation.

##  Main tasks

1. Build the method of sampling of star clusters stellar masses allowing to mimic the stochasticity of star clusters integrated photometry.

2. Build the method of automatic comparison of integrated photometry of the star cluster models to observed star clusters, to derive their parameters.

3. Determine the accuracy of the method for different photometric systems 4. Apply the method of cluster parameter derivation on real star clusters of M31 and M33.

##  Results and statements to defend

1. The method of derivation of star cluster parameters, which takes into account the stochastic sampling of star masses, allows a better derivation of the age, mass, extinction, and metallicity, compared to traditional methods, based on Simple Stellar Population models.

2. The method makes possible the derivation of star cluster metallicity based on broad-band photometry in optical and ultraviolet passbands, in the case of small photometric errors: ≤0.05 mag in optical and ≤0.15 mag in ultraviolet passbands.

3. Using a sample of star clusters of the M31 galaxy, we demonstrated the importance of the metallicity effects when trying to derive the other parameters.

4. The age, mass, and extinction parameters have been derived for a catalog of star clusters of the M33 galaxy, the typical disruption time of clusters in the M33 galaxy is ∼300 Myr and is comparable to the disruption time of clusters in M31 galaxy.

##  Presentations at conferences on thesis topic

1. de Meulenaer P., Narbutis D., Vansevičius V., Physical parameters of star clusters: stochasticity and degeneracies, "39 Lietuvos nacionalinė fizikos konferencija", 2011 October 6-8, Vilnius, Lithuania (poster presentation) 2. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Stochastic-ity effects on derivation of physical parameters of unresolved star clusters, "Reading the book of globular clusters with the lens of stellar evolution", Roma, Italy, November 26-28 d. 2012 (poster presentation) 3. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Star cluster parameters from integrated photometry: The case of WFC3@HST. Conference "European Week of Astronomy and Space Science" 2013 July 12-16, Turku, Finland (oral presentation) 4. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Star cluster parameters from integrated photometry: The case of WFC3. Conference "Evolution of Star Clusters: From Star Formation to Cosmic Ages (Annual Meeting of the Astronomische Gesellschaft)" 2013 September 24-27, Tübingen, Germany (poster presentation) 5. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving physical parameters of unresolved star clusters: age-mass-extinction-metallicity problem, "Multiwavelength-surveys: Galaxy Formation and Evolution from the early universe to today", 2014 May 12-16, Dubrovnik, Croatia (poster presented by Narbutis D.) 6. Narbutis D., de Meulenaer P., Stonkutė R., Mineikis T., Vansevičius V., Stochastic Effects in Star Clusters, "Resolved and unresolved stellar populations", 2014 October 13-17, Garching, Germany (poster presented by Narbutis D.) 7. de Meulenaer P., Narbutis D., Mineikis T., Vansevičius V., Deriving physical parameters of unresolved star clusters in the M33 galaxy, "41 Lietuvos nacionalinė fizikos konferencija", 2015 June 17-19, Vilnius, Lithuania (oral presentation)

##  Personal contribution

The author imagined and developed with the help of the publication coauthors a new method, which takes into account the stochastic sampling of star masses in star clusters, aimed to derive the cluster parameters. The co-authors participated in the interpretation of scientific results and the preparation of the publications. The author performed all the programming works, the artificial tests of the method, and the derivation of the parameters of star clusters from the M31 and M33 galaxies. In the publi-cations on the thesis topic, the contribution of the author is no lower than 70%.

##  Thesis outline

The dissertation consists of an Introduction, three Chapters, Conclusions, and the References.

Chapter 1 introduces to the problem of stochasticity in star clusters.

It is shown that the traditional Simple Stellar Population models are unfit to derive evolutionary parameters of star clusters. A grid of models taking stochastic sampling is built for the four star cluster parameters (age, mass, extinction, and metallicity).

Chapter 2 develops the method to derive the star cluster physical parameters taking into account the stochasticity problem. The method is tested on artificial star cluster samples. By use of different photometric systems, we demonstrate that the ultraviolet associated with optical is best suited for the break of degeneracies between clusters parameters.

Chapter 3 applies the method of cluster parameter derivation on real star cluster samples from two major Local Group galaxies, M31 and M33.

In M31, we use the photometric catalog from a survey performed with the Hubble Space Telescope to derive the cluster parameters, including metallicity, and hence to show the metallicity effects on accuracy of the derivation of the other parameters. In M33, we merge most recent ground-based optical catalogs and supplement near-infrared data to derive the parameters (age, mass, and extinction for all clusters, and metallicity for old ones only) of this galaxy star cluster population and constrain the rate of evolutionary fading and disruption of clusters in the tidal field of the galaxy.

##  Chapter 1

Star Cluster Models 1.1 SSP models for unresolved star clusters:

Failure and need of more elaborated models

## 1.1.1 The Simple Stellar Population models: definition

In his seminal work, Salpeter (1955) was the first to quantify the distribution of the stellar Initial Mass Function (IMF), with a simple power-law of index -2.35. This function, ϕ(m), describes how many stars of given mass m one expects depending on the mass m of the star. It essentially indicates that massive stars are much less likely than low-mass stars in a stellar population. More recently, the shape of the IMF has been found to be composed of several power-laws (Kroupa 2001), as defined in Eq. 1.2 and shown in Fig. 1.3 (a).

Isochrones are models computed for stars of same age t and metallicity [M/H], and for all masses between a lower mass m l and an upper mass m u . In the isochrones used in this thesis, based on the PADOVA stellar models (Marigo et al. 2008;Girardi et al. 2010), m l = 0.01 M ⊙ and m u = 120 M ⊙ .

These models give the flux f A (m, t, [M/H]) or magnitude M A (m, t, [M/H]) for any given photometric passband A.

From the IMF and the isochrones, we can build the concept of "Simple Stellar Population" (SSP). Indeed, stars of a stellar population following the SSP models are born at the same time and from the same progenitor giant molecular cloud, giving them the same properties: same age, metallicity, and distance to the observer (hence the same amount of extinction). The masses of the stars are built by continuously sampling the IMF. Hence, for a given photometric passband A, the integrated magnitude of the SSP model is (see, e.g., Salaris & Cassisi 2006):

The traditional photometric method used to derive the star cluster physical parameters is based on the comparison of the predicted integrated magnitudes M A (t, [M/H]) of a set of Simple Stellar Population (SSP) models of different ages and metallicities with the integrated broad-band photometry of the observed clusters, as reported, e.g., Anders et al. (2004) and Bridžius et al. (2008)(see also Narbutis et al. 2007). However, this method is strongly biased by degeneracies between parameters and by the stochastic presence of bright stars that dominate the integrated photometry. These problems are presented below.

## 1.1.2 The degeneracy problem

In the SSP models shown in the color-color diagram in Fig. 1.1, built for 13 different metallicities in the range [M/H] = 0.2 (reddest line) to -2.2 (bluest line), one can see that various degeneracies are present. Indeed, rather young star clusters of high metallicity can easily be mixed with older and lower metallicity clusters (see, for example, the region U -B ∼ 0 and B -V ∼ 0.2). If we add extinction, the SSP models at a given position are hence allowed to be degenerated with all other models situated in the direction of the arrow, creating an age-extinction degeneracy for models situated on the same SSP, or an age-extinction-metallicity for models situated on different SSPs.

## 1.1.3 The stochasticity problem

Many studies in the literature have used the SSP models to derive star cluster physical parameters (age, mass, extinction, and metallicity). However, several recent studies (e.g. Santos & Frogel 1997;Deveikis et al. 2008;Fouesneau & Lançon 2010) have brought attention on the fact that these models with continuously sampled IMF, which are unphysical, are oversimplified and biased:

• They are oversimplified because they do not take the natural disper-  (Marigo et al. 2008;Girardi et al. 2010) for 13 different metallicities in the range [M/H] = 0.2 (reddest line) to -2.2 (bluest line). The arrow indicates the extinction direction, for A V = 1 mag.

sion of integrated colors of star clusters into account, the so-called stochasticity problem. In reality, the masses of stars are stochastically sampled following the stellar IMF, and the latter could be seen as a probability distribution function (Santos & Frogel 1997). Hence, two clusters with the same physical parameters could host a different number of massive bright stars, resulting in very different integrated colors, especially in the case of young and low-mass clusters which contain only few massive bright stars. This will be shown in details in the next Section, as well as in Fig. 1.5.

• SSP models are biased because they do not even match the average of integrated color distributions for star cluster with mass1 log 10 (M /M ⊙ ) ≲ 4 (see, e.g., Fouesneau & Lançon 2010;Popescu & Hanson 2010;Silva-Villa & Larsen 2011).

As a consequence, the derivation of star cluster parameters using the SSP models can lead to severe biases, as was demonstrated by Fouesneau & Lançon (2010) (see their Fig. 3) by use of artificial tests. As an example, we show in top panels of Fig. 1.2 the derivation of age, mass, and extinction parameters using SSP models of realistic artificial clusters, simulated using a stochastic sampling of the IMF that will be developed in the next Section. In bottom panels, we show for comparison the derivation of the star cluster parameters using a method that takes stochastic sampling into account, developed in Section 2.1.

## 1.2 Stochastically sampled star cluster models

Historically, the first mention of stochastic sampling of star masses in star clusters has been introduced by Barbaro & Bertelli (1977), as they pointed out that different numbers of post main sequence stars may results in very different integrated properties of star clusters than predicted from the SSP models. They already stated that the description of the integrated color distributions of clusters cannot be performed analytically and should be done by stochastically sampling the IMF. Later cluster studies (e.g. Chiosi et al. (1988) for LMC clusters, Lançon & Mouhcine (2000)) also stressed the importance of taking into account the dispersion of integrated colors of clusters due to stochastic sampling when trying to derive their evolutionary parameters.

Santos & Frogel (1997) (see also Cerviño et al. 2002;Cerviño & Luridiana 2004;Deveikis et al. 2008) provided a scheme of the stochastic sampling on which is based the method of cluster sampling used in this thesis.

To sample the star masses in a star cluster, the IMF can be considered as a probability distribution function (PDF) that is sampled randomly between the highest and the lowest star masses. Contrarily to SSP models, this results in sampling discretely the star masses in the IMF, and not continuously. The stochasticity is introduced in the fact that bright stars are populated more sparsely than lower-brightness stars. Due to the random sampling naturally resulting in a different number of bright stars, the integrated colors of two clusters with the same physical parameters (same age, mass, extinction, and metallicity) turn out to be very different, and can also be very different from the SSP prediction.

Mathematically, here is the procedure of the sampling of the star cluster star masses, which is also illustrated in Fig. 1.3. We use the Kroupa (2001) IMF (shown in Fig. 1.3 a), defined as:

150M ⊙ , the highest physical stellar mass limit, and k and C i are the normalization constants. We then introduce the cumulative distribution function of the number of stars, nCDF, as:

which gives the number of stars contained in the cluster between the lowest mass m low to a given mass m.

Using the IMF defined above, it is possible to derive the analytical expression of the nCDF :

(1.4) where i is defined by m ∈ [m i , m i+1 ] in Eq. 1.2. generated masses of stars. In the following, this method is referred to as Random Sampling. Fig. 1.3 (c) shows the resulting sampled mass function of the generated star cluster, compared to the IMF according to which the stars have been randomly sampled.

The Random Sampling affects especially the integrated photometry of low-mass clusters. Indeed, as shown in Fig. 1.4, two generated low-mass clusters will harbor a different number of massive stars, and hence a different integrated photometry, while for massive clusters this effect will be almost negligible because they will be populated by many massive stars. Indeed, the more massive the mass of the cluster, the more populated will be the cluster in stars, and so the difference in the sampling becomes negligible for massive star clusters.

Fig. 1.5 illustrates how the stochasticity affects the integrated colors depending on their age, mass, and metallicity, for a few groups of clusters.

Each of the group is composed of 1000 clusters with the same physical parameters: the age is fixed to log 10 (t/yr) = 7, 8, 9, 10 (shown in the picture), to log 10 (M /M ⊙ ) = 3 (in blue), 4 (in green), or 5 (in red), and [M/H] = 0 (panel a), -0.6 (panel b), or -2 (panel c). As shown in the figure, the SSP models (dashed lines) are consistent with the centers of the distributions only for massive clusters, log 10 (M /M ⊙ ) = 5.

At fixed mass and metallicity, for example for log 10 (M /M ⊙ ) = 3 and [M/H] = 0 (panel a, the blue distributions), the effect of the age can be seen by the contraction of the blue distributions when age gets older (from top to bottom right). The blue and red supergiant stars present at log 10 (t/yr) = 7 (upper blue distribution) generate a strong stochasticity in the integrated colors, but they die fast afterwards, and the extent of older distributions decrease.

At fixed age and metallicity, for example for log 10 (t/yr) = 7, and [M/H] = 0 (panel a, the upper blue, green, and red distributions), the effect of the mass is visible as a contraction of the distributions when the mass of clusters gets higher. This is simply because the IMF is more densely sampled. By sampling infinitely the IMF with star masses, one would hence get the SSP positions in the color-color diagram.

The metallicity effect, from the panel (a) to the panel (c), is illustrated by a change of the positions of the groups. This can be already seen using SSP models, as in Fig. 1.1, where the most metallic SSP (reddest line) extends much more in the red direction, in the U -B versus B -V diagram, than the SSP with lowest metallicity (blue line).

In Section 1.3, we present a refinement of the Random Sampling, the Reduced Random Sampling method. Indeed, it is believed that the extent of stochasticity in the sampling of star mass in clusters may be lower than the Random Sampling, which would be an upper limit, but still contain more stochasticity than the Optimal Sampling (Kroupa et al. 2013), which states that star masses are built deterministically2 .

## 1.3 The Reduced Random Sampling Method

This Section, which has been the object of a paper (de Meulenaer et al. 2014b), contributes to the debate existing nowadays between the two extreme proposed schemes on the way stellar masses are sampled within star clusters, which are the Optimal Sampling and the Random Sampling of stellar masses. We propose a new method of sampling of stellar masses which allows a continuous transition between the Optimal Sampling and the Random Sampling of star clusters. We use a sample of young star clusters available in the literature to calibrate the amount of stochasticity generated by the proposed method.

## 1.3.1 Introduction to the Reduced Random Sampling idea

The aim of this Section is to tackle the problem of the influence of the stellar mass sampling in star clusters on the stochasticity of their integrated colors. Indeed, it is still undefined how the stellar masses should be sampled from the initial mass function (IMF). On one hand, several studies (e.g., Santos & Frogel 1997, Deveikis et al. 2008, Fouesneau & Lancon 2010) implement a random stellar mass sampling from the IMF. In this view, the IMF is seen as a probability density function, according to which stellar masses are randomly drawn. This is referred to as Random Sampling (RS). On the other hand, other studies (e.g., Weidner et al. 2010, Weidner et al. 2013, Kroupa et al. 2013) propose the idea that the stellar masses could be an Optimal Sampling (OS) of the IMF. In that view, the mass of the most massive star is exactly determined by the mass of the zero-age star cluster (Kroupa & Weidner 2003;Pflamm-Altenburg et al. 2007;Weidner et al. 2010). Then the mass of the second most massive star is related to the mass of most massive one, the mass of the third star to the mass of the second, and so on recursively all stellar masses are generated (see equations 9-11 of Kroupa et al. 2013 for details of the Optimal Sampling scheme). Hence, for a given star cluster, there is a deterministic link between the masses of its stars and the cluster's mass. This view is supported by observations of the most massive stars of very young clusters (see compilation of such observations in Weidner et al. 2013) where a trend between the mass of the most massive stars and the mass of their host clusters seems to exist.

In this Section, we present a new sampling method, referred to in the following as a Reduced Random Sampling (RRS), which can be seen as a continuous transition between the two extremes that are the RS and the OS. The idea of the method is to allow a two-parameters variation to tune the extent of stochasticity that can be decreased to zero-stochasticity (i.e., OS) or increased up to full stochasticity (i.e., RS). Then the compilation of young clusters of Weidner et al. (2013) is used to constrain the best value of the parameter guiding the extent of stochasticity.

## 1.3.2 Presentation of the method of Reduced Random Sampling

Recently, Popescu & Hanson (2014) presented a sampling method based on the Optimal Sampling (OS). In their method, the mass bins are defined around each stellar masses derived from Kroupa et al. (2013) OS method, so that the stars are resampled in these bins, introducing a small stochasticity in the mass function. However, one could argue that in this process, the amount of stochasticity is not constrained by observations.

Here we propose a new sampling method, the Reduced Random Sampling, schemed in Fig. 1.6, which can be considered as a continuous transition between the OS and the Random Sampling (RS). Here we mention the four main steps, that we develop in the following:

1. Generate stellar masses using the OS for a star cluster model of given mass.

2. Define bins around the masses of OS generated stars.

3. Expand or shrink the bin widths by a defined expansion factor value, P . For bins defined in step 2, P = 1. When bins are expanded, P > 1, when bins are shrunk, P < 1.

4. Resample the mass of the star within the modified bin defined around it.

The effect of the P factor, controlling the width of the bins is illustrated in Fig. 1.6 (P is specified on tops of panels). If we shrink the sizes of the mass resampling bins (P → 0), as sketched in the first column of panels in log 10 (m/M )

Fig. 1.6. Scheme of the Reduced Random Sampling method, allowing a continuous transition between the Optimal Sampling (OS) and the Random Sampling (RS).

The columns of panels present results obtained with different values of expansion factors, P , shown on the top of panels. The first two rows of panels present the cumulative distribution function and the IMF respectively. These panels describe the transition between the OS and the RS, schemed for 2 stars, one in the lowmass regime and another in the high-mass regime of the IMF. For each stellar mass built by the OS, a bin is defined around the mass of the star. For purpose of illustration, the bin in the low-mass regime has been enlarged by a factor 200 in linear scale. In these mass bins, the stellar masses are resampled. The third row presents the relation between the mass of the most massive stars vs the mass of their host clusters compared to the Weidner et al. (2013; green solid line) and Kroupa et al. (2013; cyan long-dashed line) relations. The oblique black dashed line is the identity relation between the mass of the most massive stars and the mass of the host clusters, m max = M , and the horizontal black dashed line is the physical upper limit of massive stars, 150 M ⊙ . In fourth row, the impact of the increase of the stochasticity in the cluster stellar mass sampling on the color distributions of these cluster models is shown. The cluster models shown have mass log 10 (M /M ⊙ ) = 4, with age log 10 (t/yr) = 7, 8, 9 (blue, orange, red).

Fig. 1.6, no stochasticity is produced; it is the Optimal Sampling case. On the contrary, if we expand the bins two times (P = 2, second column of panels in Fig. 1.6), we generate stellar masses which are close to the ones of OS, hence with small stochasticity in the mass function. If we expand more the mass resampling bins, as sketched in third column of panels in Fig. 1.6

(P = 6), we allow the stellar masses to be resampled further from the masses given by the OS, resulting in enhanced stochasticity. By expanding the mass resampling bins very widely, the method then reaches RS (the last column of panels in Fig. 1.6).

In Fig. 1.6 the impact of shrink and expansion of the mass resampling bin can be seen on the scatter of the most massive stellar mass versus the mass of the host star cluster (third row of panels) and on the distribution of the integrated colors of these star clusters (last row of panels). The bin expansion increases stochasticity in the integrated photometry of clusters.

In step 1, Stellar masses are first optimally sampled using the method of Kroupa et al. (2013). We use the OS algorithm from Pflamm-Altenburg & Kroupa (2006) 3 . In the OS method, any most massive star mass, m max , of a given host cluster of mass M follows exactly a theoretical relation, shown by long-dashed cyan line in Fig. 1.7. However, we modified the OS so that the most massive star mass m max of a given cluster of mass M follows exactly the empirical relation of Weidner et al. (2013), shown in green solid line in Figs. 1.6 and 1.7, as it closer represents the observations (shown in Fig. 1.7).

In step 2, we define a bin around each OS star position. The limits of the bin are located at half distance in mass space between the star and its lower and higher mass neighbors. This bin width, w OS , corresponds to the case when the expansion factor is P = 1.

If we randomly generate stars in each of the bins defined, the mean of the generated mass in each bin will not necessarily be equal to the mass of the OS star of the bin. However, this should be the case to ensure that the mass function of the cluster is conserved. To guarantee this, we slightly shift the bins, keeping their width w OS constant, so that the means of the bins coincide with the OS stars. For each bin, this consists in searching the  Weidner et al. (2013;red points). For comparison, artificial star cluster distribution of 1 000 models built with the Reduced Random Sampling method, with the calibrated mass bin expansion factor P = 6 (black points) and the correction parameter d = 0.2 (see details in Section 3 on parameter d), and with addition of errors of the same magnitude as for observations. The cyan long-dashed line is the theoretical relation derived by Kroupa et al. (2013) and the green solid line is the third order polynomial fit to the data of Weidner et al. (2013). The oblique black dashed line is the identity relation between the mass of the most massive stars and the mass of the host clusters, m max = M , and the top black dashed line is the physical upper limit of massive stars, 150 M ⊙ .

so that we respect the condition4 :

where nCDF is the IMF number Cumulative Distribution Function (shown in first row of Fig. 1.6) and mCDF is the mass Cumulative Distribution

Function. Here we derive them.

We use the Kroupa (2001) IMF (shown in Fig. 1.6) that was defined in Eq. 1.2. The nCDF and mCDF are then defined as:

and

(1.7)

The analytical expressions of nCDF and mCDF are:

(1.8) and

(1.9)

where i is defined by m ∈ [m i , m i+1 ] in Eq. 1.2.

As a and b are related by w OS = b -a, Eq. 1.5 is solved for each bin. Thus, the mass generated in the bin is on average the same as the OS mass in that bin.

In step 3, the bins of all stars are expanded by multiplying their widths by an expansion factor, w = P • w OS . Then each star is resampled in its individual bin. We could see the resampling as the application of the RS used in, e.g., Santos & Frogel (1997), but restricted to the bins defined around each OS star position. The mass bins can be expanded for a transition toward RS (P → ∞) or shrinked for a transition toward OS (P → 0). Fig. 1.8 shows the optimally sampled massive stars (gray vertical lines) of a log 10 (M /M ⊙ ) = 4 star cluster, and the resampling bins for a few of them (the colored rectangles), for different expansion factor P values. When the bins are expanded too much, they can exceed the high-mass limit, 150 M ⊙ .

To avoid this, we group stars belonging to such bins and resample them within a common bin. In Fig. 1.8 (c), the black bin is a common bin for the red, blue, and green stars of panels (a) and (b). The high-mass limit of the common bin is fixed to b = 150 M ⊙ , and the low-mass limit a is found by In the case of large enough expansion factor (c), the resampling bins of the three most massive stars (red, blue, and green) are grouped in a common bin (shown in black), in which they will be resampled. The mean mass of the bin is the mean of the OS masses of the three stars, shown in black thick vertical dashed line. The thin vertical dashed line shows the high-mass limit, 150 M ⊙ .

requiring that the mean mass of the common bin equals to the mean mass of the OS stars grouped into the common bin:

where n is the number of grouped stars, e.g., n = 3 in Fig. 1.8(c).

In a similar way, for low-mass stars close to the low-mass limit with a = 0.01 M ⊙ , a common bin is also defined by searching for the high-mass limit b.

When generating stars with the sampling algorithm described until here with bin widths defined as w = P • w OS , we observe a problem in the m max vs M relation, displayed in the first column of panels in Fig. 1.9. Indeed for several expansion factors (see cases P = 4, 6), stars in low-mass clusters (log 10 (M /M ⊙ ) ∼ 2.5) almost reach the physical stellar mass limit, while it

is not yet the case for more massive clusters. The reason is that when we sample the stellar masses with the Optimal Sampling, a low-mass cluster contains less stars than a massive cluster. Thus the stars of the low-mass cluster are more distant in the mass space, creating larger bins around them.

For the expansion factors P = 4 and 6, we see that this can create more massive stars in the low-mass clusters than in the more massive ones, which is unlikely to be true, considering the Weidner et al. (2013) observations (see red dots in Fig. 1.7).

We applied a correction as a dependence of the bin width on the mass of the cluster:

As emphasized in Fig. 1.9, the choice of the power-law index, d, is guided by the fact that for d = 0 (see first column of panels), the effect is present, and for high power-law index (d = 0.4, see last column of panels), the m max scatter present in massive clusters dominates too much, while it is reduced in low-mass clusters.

## 1.3.3 Calibration of the Reduced Random Sampling

To calibrate the best value of the parameters (P, d), we compare the observational data of Weidner et al. (2013) with the models built with the Reduced Random Sampling method (see Fig. 1.7). We note that the error bars of cluster mass and most massive star mass provided by Weidner et al. (2013) are not statistical quantities but are just lower and higher possible limits. They derived the masses of the most massive stars using their spectral classes and assumed an error range as 1/2 of the spectral subclass.

For the masses of the clusters, they have extrapolated them from the visible stars of the clusters using the IMF (Kroupa 2001). The upper mass limit was derived assuming that all stars could be unresolved binaries and for

Fig. 1.9. Dependence of the stochasticity affecting the most massive stars of star clusters on the d power-law index (indicated on the top of panels) and on the expansion factor, P , indicated on the right of panels. The first column of panels describes the sampling when no correction is taken into account, d = 0, while the central and right columns show the sampling generated with a growing correction. Each panel contains 1 000 cluster models.

the lower limit that half of the stars are misidentified as cluster members, foreground or background objects.

We need a statistical description of the uncertainty to introduce it into the cluster models, and assume that it can be described by a Gaussian distribution with a sigma taken as 1/3 of the Weidner et al. (2013) error bars, meaning that these error range limits contain 99% of the measures.

We built several model distributions having different (P, d) parameters and we added errors of the same sigma as defined above. we derive the likelihood l i between the histogram of the models minus OS relation and the histogram of the observations minus OS relation. Then a total likelihood L is derived as a product of the likelihoods l i of each group.

The result is presented in Fig. 1.10, where the minimum is found in P = 6,

We adopted these parameter values for the distribution shown in Fig. 1.7, compared to the Weidner et al. (2013) observations. The few deviating observations do not influence significantly the selection of the best expansion factor, as we got the same values of P = 6 and d = 0.2 when we neglected them. Note that Weidner et al. (2013) indicate that the error ranges do not take into account other sources of errors like variable extinction, stellar variability, star loss due to gas expulsion and dynamical interactions. Hence, it is likely that the true expansion factor P could be smaller than the one found here, which therefore should be regarded as an upper limit. The increase of data and the refinement of errors in Weidner et al. (2013) sample would help to constrain more accurately the values of the parameters (P, d).

## 1.3.4 Summary: the Reduced Random Sampling

In this Section, we presented a new sampling method of stellar masses in clusters, the Reduced Random Sampling, which allows a continuous transition between the Optimal Sampling and the Random Sampling, already widely used in unresolved cluster studies. Then, using the catalog of young star clusters from Weidner et al. (2013), we constrained the parameters controlling the level of stochasticity in artificial clusters. In the following of this thesis, the sampling scheme used to build stochastic models will remain the Random Sampling method presented in Section 1.2. The Reduced Random Sampling presented in this Section is a refinement that still demands to be confirmed with additional observations in the following years.

## 1.4 Model grid for age, mass, extinction, and metallicity

To derive the physical parameters of unresolved star clusters, we computed a large 4-dimensional grid of discrete cluster models for the age, mass, extinction, and metallicity, randomly sampling the stellar mass according to the initial mass function (IMF, Kroupa 2001) following the method based on Santos & Frogel (1997), described in Section 1.2. Each node of the grid contains 1 000 star cluster models. The star luminosities are derived from stellar isochrones of the selected age and metallicity of the cluster models. We used the PADOVA isochrones5 from Marigo et al. (2008) with the corrections of Girardi et al. (2010) for the TP-AGB phases. The grid was built according to the following nodes: from log 10 (t/yr) = 6.6 to 10.1 in steps of 0.05, from log 10 (M /M ⊙ ) = 2 to 7 in steps of 0.05, and for 13 metallicities: from [M/H] = 0.2 to -2.2. This gives a grid of 71 values of age, 101 values of mass, with 1 000 models per node, hence ∼7 × 10 6 models for each metallicity. To limit the number of models that need to be stored in computer's memory, extinction was computed when the observed cluster is compared with the grid of models. It ranges from E(B -V ) = 0 to 1 in steps of 0.01, therefore 101 values for the extinction. We used the Milky Way standard extinction law from Cardelli et al. (1989) for star clusters situated in M31, believed to have a similar extinction law as the Milky Way, or LMC extinction law of Gordon et al. (2003) for star clusters situated in M33, believed to have a similar extinction law as the LMC. With the construction of this age-mass-extinction-metallicity grid of stochastic star cluster models, one can derive consistently the star cluster parameters, as presented in the next chapter.

Chapter 2

Deriving the Cluster Parameters

## 2.1 The method of star cluster parameters derivation

The main idea of the method for deriving the physical parameters (age, mass, extinction, and metallicity) of a given observed star cluster with available broad-band photometry is to compare its magnitudes with those of a 4-dimensional grid of models for every value of the four physical parameters. Each node of the model grid described in the previous section contains a large series of models of the same age, mass, extinction, and metallicity to represent stochastic variations in photometry.

Here is the first method of derivation of the star cluster parameters. A 4-dimensional grid of cluster models is built for every value of the four physical parameters, log 10 (t/yr), log 10 (M /M ⊙ ), E(B -V ), [M/H] ; for simplicity Fig. 2.1 (a) shows only a grid for age and mass. For the description of the sampling method to generate cluster models, see Section 1.2, and for the description of the grid, see Section 1.4. Each node of the grid contains 1 000 models of the same age, mass, extinction, and metallicity. They populate the photometric parameter space (absolute U BV RI magnitudes). When the observations are considered in Fig. 2.1 (c), along with their error bars (σ; hereafter we use σ = 0.05 mag for all the passbands of artificial and real cluster samples studied in Chapter 3 unless specified otherwise), which in general can be different for every magnitude, all the models situated within 3-σ from the observed magnitudes are selected. Fig. 2.1 (d) shows the nodes to which the selected models are associated. Other nodes do not play any role in the derivation of parameters. Finally, the distri- For the selected models (Fig. 2.1 (c), red circle) we apply weights as follows: for the models located within 1-σ from the observed magnitude a weight of 0.68 is assigned, for the ones between 1-σ and 2-σ a weight of 0.28, and for the ones between 2-σ and 3-σ a weight of 0.04. The probability density distributions displayed in Figs. 2.1 (e, f) are derived by normalizing the total area of each histogram to 1. The solution is taken as the maximum of these 1-dimensional distributions. We compute confidence intervals (error bars) by excluding the first and the last 16% of the area in histograms, following the method of "central interval" presented in § 2.5.1 of Andrae (2010).

The second method is a mathematical generalization of the first method. In a similar way as Fouesneau & Lançon (2010) and Fouesneau et al. (2014), we evaluated the likelihood of each node of the grid to represent the magnitudes of a given observed cluster. For each node, we first computed the likelihood of each model from the node by

where f stands for one particular passband, mag f for the observed and model magnitudes in that passband, and F for the total number of passbands, for example 5 for the U BV RI photometric system. Then the likelihood of the node of age t, mass M , extinction E(B -V ), and metallicity

[M/H] is the sum of the likelihoods of its models,

where N is the total number of models contained in the node. The observed star cluster is then classified with the parameters of the node, which maximizes L node among all nodes of the grid.

Note that this procedure could be also applied by using colors (e.g.

U -B, u * -g ′ , or other passbands combinations) in place of individual magnitudes, in the variable mag f of Eq. 2.1. In this thesis, we will use the method applied on magnitudes unless explicitly expressed otherwise.

## 2.2 Improvement on the derivation of parameters

This section presents a third method of derivation of star cluster parameters and is the object of a paper in preparation (in which the method will be released for public use). This method is an analytical generalization of the second method presented in 2.1. Cerviño & Luridiana (2006) made an unfruitful attempt to find a complete analytical method of derivation of star cluster physical parameters when their colors are integrated, which takes stochasticity into account.

Present-day methods of derivation of star cluster parameters, which take the stochasticity problem into account, are based on a large age-massextinction (and metallicity, in our case) grids of star cluster models. For each node of the grid, a large collection of models is built to reproduce the stochastic distribution of colors (or magnitudes) of the clusters for these In this Section, we developed a method which aims to solve this problem. The idea is to replace the large collection of models for each node by a multivariate Gaussian Mixture Model (GMM), which would analytically describe the grid. Each node of the grid, containing 1 000 models (or more) can be approximated by a collection of multivariate (i.e. multidimensional, for example in the U BV RI passband space) Gaussian functions f i with corresponding weights ϕ i . With a high enough number of such Gaussian functions, virtually all shapes in the photometric space could be efficiently reproduced by use of the Expectation-Maximization algorithm (EM, Dempster et al. 1977).

Mathematically, each node can be described as a probability distribution function (PDF), which is the sum of the Gaussians components:

where ⃗ x is a vector containing the different magnitudes of the observed cluster, ⃗ µ is the vector containing the different magnitudes of the mean of the component i, Σ i is the covariance matrix which shapes each of the i Gaussian components f i , and ϕ i is the weight of each Gaussian component

is the PDF of the component i, which can be written as:

where D is the number of dimensions in the photometric space, for example D = 5 for the U BV RI space.

The weighted sum of the functions

is the analytical generalization of the discrete PDF of a given node (see Eqs. 2.1 and 2.2). Hence, to derive the parameters of an observed cluster, we have to maximize the likelihood of the node, given in Eqs. 2.3 and 2.4, i.e., to search the node that maximizes the quantity

We used the GMM algorithm from scikit-learn1  (Pedregosa et al. 2011) and found that the composition of 10 Gaussian models can efficiently reproduce the stochasticity for any composition of parameters, hence any node of the grid. Fig. 2.2 illustrates the comparison of such GMMs and corresponding nodes of discrete Monte-Carlo models. The blue circles in top panels of Fig. 2.2 are 1 000 star cluster models generated by random sampling, constituting one node from the discrete grid, with age log 10 (t/yr) = 7, mass log 10 (M /M ⊙ ) = 3, and metallicity [M/H] = 0. The density plots in bottom panels are the associated GMM models for this node. This GMM models can be seen as a PDF and hence discrete samples can be generated from them, such as the green circles shown for comparison to the real cluster models in top panels of the figure. Fig. 2.3 shows the same comparison for an other node of the grid, older (log 10 (t/yr) = 8) and more massive (log 10 (M /M ⊙ ) = 4).

Using this approach allows to speed up the derivation of star cluster parameters by a factor 10. Also, a very interesting advantage of this GMM method is that it can be based on a grid of models composed of 1 000 models per node, or 10 000 models per node or even more; it will be the same room in memory, as nodes are compressed in a few numbers describing the analytical Gaussian mixture.

To summarize, the GMM approach: • allows to describe a grid of node efficiently, by contracting it to a given number of GMM parameters,

• allows an analytical derivation of the star cluster physical parameters, avoiding the long process of derivation of likelihood of each of the 1 000 models in each node in the approach presented in Section 2.1 .

## 2.3 Test of the method with an artificial cluster sample

We simulated artificial star cluster samples with known age, mass, extinction, and metallicity and used them as input clusters to evaluate the ability of our method to derive physical parameters. The artificial cluster samples consist of 10 000 clusters with ages uniformly distributed in the log 10 (t/yr) range [6.6, 10.1]. To simulate the mass of input clusters, we used a powerlaw cluster mass function with index -2 in the range log 10 (M /M ⊙ ) = [2.7, 4.3], so as to have more low-mass clusters in the sample. We have two artificial samples: one without extinction and the other with E(B -V ) (uniformly distributed) in the range [0, 1] using the Milky Way standard extinction law from Cardelli et al. (1989). In this Section, the metallicity is fixed to [M/H] = -0.4. The effects of metallicity will be studied in Sections 2.4, 2.5, and 2.6. In Fig. 2.4 (b), the asymmetry observed in the mass derivation slightly favors high masses. This is because, in the grid of star cluster models, the nodes of models with higher mass have magnitudes that are less dispersed than the nodes with lower mass models, as a consequence of stochasticity (as it has been shown in Fig. 1.5). Thus, when the models of two nodes of different masses are located in the U BV RI "sphere" around the observation  It creates two streaks above and below the one-to-one relation in the range of 8 ≲ log 10 (t/yr) ≲ 9.5 that were already perceptible in the case without photometric errors in Fig. 2.5 (a). However, including of photometric errors does not significantly affect the derivation of mass (panels b and e). We note that a gap in derived ages at log 10 (t/yr) = 9.15 is a feature of isochrone due to the increase in the production rate of AGB stars, which was discussed in Girardi & Bertelli (1998).

These degeneracy streaks have first been reported by Fouesneau & Lançon (2010). The degeneracy streak above the one-to-one line seen in Fig. 2.5 (d) concerns clusters that are young and that possess intrinsically high extinction, but are derived by the method as older and having lower extinction. Conversely, the streak of clusters below the one-to-one relation involves objects that are derived as younger and that have higher derived extinction than they do in reality. These features are important to keep in mind when deriving the physical parameters of unresolved star clusters.

## 2.3.1 Is it possible to reduce the age-extinction degeneracy?

The upper and lower streaks in Fig. 2.5 (d) suggest that if a wide extinction range is allowed in a simulated sample, then there are possibilities that a

cluster mimics an older one with lower extinction, or inversely a younger one with higher extinction. If the true extinction range of the cluster population is narrow, then we could restrict the search for the extinction within a narrow range in the model grid, resulting in decrease of age-extinction degeneracy.

In Fig. 2.6 we show results of the tests for a sample of 10 000 artificial clusters with true extinction from a range of E(B -V ) = [0, 0.5] and with Gaussian photometric errors of 0.05 mag randomly added to each magnitude of the sample clusters. This cluster sample was studied twice, with different allowed extinction ranges in the model grid.

In the first test, the extinction of the model grid was allowed to vary in a wide range, E(B -V ) = [0, 1], shown in Fig. 2.6 (a,b,c). If a cluster has a true extinction of 0.5 mag, then the maximum underestimation of its extinction can be from 0 to 0.5 mag. But if a cluster has true extinction of 0, the maximum overestimation of its extinction could range from 0 to 1 mag. This explains why the lower streak (i.e. clusters with overestimated extinction) is more extended than the upper one in panel (a).

In the second test, the allowed extinction range of the model grid was reduced to a range of [0, 0.5]; Fig. 2.6 (d,e,f). The constraint on the extinction range resulted in a reduction of the lower degeneracy streak, seen in Fig. 2.6 (d), which is less developed than in Fig. 2.6 (a). From the comparison of Figs. 2.6 (b) and (e), we see that the mass is less affected by the degeneracy. We note that only the lower streak is modified, since only the higher limit of the allowed extinction range was changed from 1.0 to 0.5 mag. The upper streak is not modified, because the lower limit of the allowed extinction range was not changed.

To quantify the reduction of the lower degeneracy streak due to reduction of the extinction range, all the models situated in the square shown in We conclude that to reduce the degeneracy streaks seen in Fig. 2.5 (d), we should make a reasonable assumption on the extent of the possible extinction range within the galaxy hosting the studied cluster population.

## 2.4 Metallicity effects: one-metallicity vs onemetallicity

To characterize the sensitivity of the accuracy of the method presented in Section 2.1 on the metallicity parameter, we built samples of 10 000 stochastic artificial clusters with a uniform random distribution in the age range log 10 (t/yr) = [6.6, 10.1] and a uniform random distribution in the extinction range E(B-V ) = [0, 1], with the mass fixed to log 10 (M /M ⊙ ) = 4 and for 3 metallicities, [M/H] = 0, -0.6, and -2. These artificial clusters were built with photometry available in the optical (U BV RI), near-infrared (JHK), and ultraviolet (GALEX) passbands.

## 2.4.1 Parameter derivation for artificial clusters in U BV RI

In this first test, we show the results of deriving age, mass, and extinction using U BV RI passbands alone. Photometric errors were included in the U BV RI photometry of artificial clusters by adding Gaussian errors of σ =  The panels above and below the main diagonal panels of Fig. 2.7 show the results where the metallicity of the grid is different from the true one, therefore additional biases appear. For the age parameter (panels block a)

we observe a reinforcement of the left part of the age-extinction degeneracy streak when the grid metallicity is lower than the true metallicity (panels above the main diagonal panels) and a reenforcement of the right part of the streak when grid metallicity is higher than true metallicity (panels below the main diagonal panels).

Essentially, when the grid metallicity is higher than the true metallicity (panels below the main diagonal panels), the underestimation of the ages of old clusters can be understood because, for the same age, mass, and extinction, low-metallicity clusters are generally brighter and bluer than high- metallicity clusters. This is why classifying low-metallicity clusters with a higher-metallicity grid will interpret this brightness as that of younger clusters. Moreover, the degeneracy exists not only between the age and metallicity: the clusters are perceived to be much younger than they are, but also less massive (Fig. 2.7 b). The extinction (Fig. 2.7 c) is also affected, so that the degeneracies are strongly multidimensional. The reverse effects are also true for the upper main diagonal panels, when the grid metallicity is lower than the true one. Out of main diagonal results show how much derived parameters would be biased when trying to derive their values for unresolved clusters using an incorrect metallicity for the model grid.

## 2.4.2 Addition of near-infrared passbands: U BV RI + JHK

By using simple stellar population models (SSP), Bridžius et al. (2008) (see also Anders et al. 2004) showed that adding near-infrared information (JHK photometric bands) to optical U BV RI passbands could help to significantly decrease the age-extinction degeneracy. We performed the same tests with stochastic clusters with additional JHK passbands. In each JHK passband, we added Gaussian photometric errors of σ = 0.1 mag to mimic the larger photometric uncertainties present in these passbands.

We kept σ = 0.05 mag for the Gaussian photometric errors added to the U BV RI passbands.

The results are displayed in Fig. 2.9. The main diagonal panels of the age and extinction parameter blocks (respectively a and c) show that the ageextinction degeneracy is reduced significantly. The streaks perpendicular to the one-to-one dashed line in the age parameter block (Fig. 2.9 a) are much less populated than when only U BV RI passbands were used (Fig. 2.7 a).

The decrease of intensity of the age-extinction degeneracy is also visible in Fig. 2.8 (second row), compared with the case without JHK passbands (first row).

However, out of the main diagonal panels of Fig. 2.9, hence when the grid metallicity is different from the true metallicity of clusters, the strong additional biases due to metallicity seen in U BV RI-only case are still present, despite some minor differences.

## 2.4.3 Addition of ultraviolet passbands: GALEX + U BV RI

It is well-known (e.g., Kaviraj et al. 2007) that the association of far-ultraviolet (FUV) and near-ultraviolet (NUV) passbands with optical U BV RI passbands helps in reducing degeneracies in the derivation of parameters. Here we study the samples of 10 000 stochastic artificial star clusters with U BV RI photometry, with σ = 0.05 mag for the photometric Gaussian errors, and GALEX photometry with σ = 0.15 mag for each of the FUV and NUV passbands.

Fig. 2.10 shows the results for this passband combination, sharply constraining the age, mass, and extinction. The age-extinction streaks present in main diagonal panels in previous tests (Fig. 2.7 and 2.9) here vanish entirely. This is also clear in the last row of panels of Fig. 2.8, where the correlation present in U BV RI and U BV RI + JHK cases fades.

The break of the age-extinction degeneracy brought by ultraviolet data can be understood in Fig. 2.12. Panel (a) shows the SSPs of the 13 metallicities in optical passbands alone as well as the distributions of 1 000 discrete cluster models of mass log 10 (M /M ⊙ ) = 4, of age log 10 (t/yr) = 7, 7.5, 8, 8.5, 9, 9.5, and 10, for three metallicities: [M/H] = 0, -0.6, and -2. In that case, for a given SSP of fixed metallicity, the bending of the SSP curve at intermediary ages and the direction of the reddening vector allow an ageextinction degeneracy between young and old clusters. This is also true in terms of discrete model distributions, because the distributions of a given metallicity follow the SSP line of the corresponding metallicity. Fig. 2.12 (b)

shows that this is not anymore the case when ultraviolet data are used, as the reddening vector now strongly deviates from the SSP direction.

However, as seen in previous tests, offsets are also observed in Fig. 2.10 (a) when the grid metallicity is different from the true one (out of main diagonal panels), but the scatter is much smaller here. As before, when the metallicity of the grid is higher than the true one (panels below the main diagonal panels), the age is classified as younger and the mass as lower, and the reverse is true when the grid metallicity is lower than the true one (panels above main diagonal panels).

Note, however, that these results are in practice not useful for clusters older than a few hundred million years, as the FUV and NUV magnitudes strongly fade later on (see, e.g., Bianchi 2011). This means that to estimate the parameters of star clusters of close galaxies such as Andromeda or Triangulum, GALEX data can only be used for young clusters because for older clusters ultraviolet photometry falls below the detection limit.

## 2.5 Metallicity effects: one-metallicity vs whole metallicity range

In this Section we present the derivation of star cluster parameters when the metallicity of the model grid extends on a wide range. The aims are to see how much the derivation of the age, mass, and extinction deteriorates compared to the case where the metallicity is fixed to the correct value, and also to see if we can derive a reliable estimation of the metallicity parameter itself.

It is good to remember that the sensitivity of a photometric system to age and metallicity parameters can vary strongly, depending on which spectral area it is situated in. This is presented in Fig. 2.11, where the spectra of SSP models (built using PEGASE package2 , Fioc & Rocca-Volmerange 1999) are  We study the parameter derivation of three artificial clusters samples, each of them with one fixed metallicity ([M/H] = 0, -0.6, and -2), using a large grid containing cluster models of 13 different metallicities (from

2), to determine the ability of the method to derive the cluster age, mass, and extinction when the metallicity is unknown, with an attempt to also constrain the metallicity itself. First, we apply the method using only U BV RI photometry, then using U BV RI + JHK photometry, and, finally, using GALEX + U BV RI photometry. As previously, the mass of clusters was fixed to log 10 (M /M ⊙ ) = 4, and the models were   In Fig. 2.12 (a), the age-extinction degeneracy exists for each given SSP with fixed metallicity. When we derive the cluster parameters allowing all metallicities, we see that the age-extinction degeneracy now extends between SSPs (and also between the discrete model distributions) of different metallicities, enlarging the uncertainty in deriving these parameters.

In addition to the reinforced age-extinction degeneracy, deriving the metallicity is complicated by the fact that in the optical passbands the SSPs (or the discrete model distributions of corresponding age) are naturally close and overlapping for young and intermediate-age clusters, so that the distance between them in photometric space is small compared with typical photometric uncertainties. These two problems make the U BV RI photometric system unsuitable in deriving the metallicity.

In Fig. 2.13, we define regions around the true metallicities (shaded area ±2 bins around the vertical line in bottom panels), in which we quantify how many solutions are found in these regions. For example, for clusters with true metallicity [M/H] = -0.6 (central case of Fig. 2.13 a), only ∼20% of clusters are classified with a metallicity in the region around the true metallicity when only U BV RI is used. The accumulation of solutions at the metallicity range boundaries can be interpreted as that the derived metallicity of these clusters could be located even farther away from the true values, if the range of metallicities were broader.  tion, the age panels show that adding ultraviolet information completely discards the streaks perpendicular to the one-to-one black dashed line. Fig. 2.12 (b) shows that young clusters cannot be degenerated with old clusters through the age-extinction degeneracy, which facilitates the age and mass derivation. The scatter around the true mass is also more strongly reduced than for U BV RI and U BV RI + JHK cases. The metallicities are now better derived as well, even when the true metallicity is [M/H] = -0.6, the boundary effects are significantly reduced. Moreover, at least half of the clusters are classified with the correct metallicity when ultraviolet data are added to the optical. In Fig. 2.12 (b) and (c), the SSPs (and also the discrete model distributions) overlap much less than in the optical passbands. In Fig. 2.12 (c), the combination of far-ultraviolet with optical U passband allows us to distinguish between different metallicities, as the reddening vector is now nearly parallel to the SSPs (especially at young ages) and that the SSPs are more spaced, compared with the error bars (see the zoom plot). It is also interesting to note that, because the reddening vector points in different directions in Fig. 2.12 (b) and (c), it is not possible to degenerate two discrete model distributions of different metallicities by means of extinction.

In Fig. 2.14 the same tests were performed with artificial clusters without any extinction added to their photometry (E(B -V ) = 0), and classified considering the extinction as a known parameter, leaving only the age, mass, and metallicity as free parameters. Now, without degeneracies introduced by extinction, the derivation of the other parameters is much more accurate. For all photometric systems, the effect of the metallicity on the age derivation manifests itself through a slight shift of the ages above or below the one-to-one black dashed line. Concerning the metallicity derivation, one can see that even in this case when there is no extinction, a consistent derivation of the metallicity with only U BV RI passbands is not possible, despite a strong decrease of boundary effects on the metallicity, compared with the case where extinction was included (compare Figs. 2.13 and 2.14). For example, only ∼35% of clusters are classified in the region of the correct metallicity when the true metallicity is [M/H] = -0.6. Using U BV RI + JHK, the metallicity of clusters is better derived than in the case with unknown extinction, and the metallicity boundary effects are decreased. In the worst case, at least ∼55% of clusters are classified with a correct metallicity. Hence, the break of degeneracies with metallicity can be efficiently achieved with U BV RI + JHK photometric system only when the extinction is well constrained beforehand. For GALEX + U BV RI, the metallicity prediction only slightly improves when there is no extinction, compared with the case when there is extinction.

## 2.6 Exploration of the metallicity effects for the WFC3 photometric system onboard HST

## 2.6.1 One-metallicity vs one-metallicity test

We apply the method of star cluster parameter derivation using the WFC3 photometric system: UVIS1/F275W, UVIS1/F336W, ACS/F475W, ACS/F814W, IR/F110W and IR/F160W to characterize the ability of this photometric system to derive the physical parameters of clusters. We study this particular photometric system because a M31 star cluster sample with photometry obtained in this system will be studied in Section 3.2. The photometric passbands of this photometric systems can be seen in bottom panel of Fig. 2.11, where they are compared to the passbands of the U BV RI+JHK and GALEX ones (central panel).

We generated 3 samples of 10 000 artificial star clusters with uniform random age in the range log 10 (t/yr) = [6.6, 10.2], mass fixed to log 10 (M /M ⊙ ) = 4, with uniform random extinction in the range E(B -V ) = [0, 1]. Each of the 3 samples has a fixed metallicity, [M/H] = 0, -0.6, or -2. Gaussian photometric errors of σ = 0.05 mag were added to the magnitudes of the artificial clusters for each passband.

In this test we derived the age, mass, and extinction of clusters using model grids of fixed metallicity ([M/H] = 0, -0.6, or -2), and the results are displayed in Fig. 2.15. Comparing Fig. 2.15 to pure optical case (U BV RI) or optical + NIR case (U BV RI + JHK) shown in Section 2.4, the presence of the UV passband (here UVIS1/F275W) helps significantly to narrow the scatter in derived age, mass, and extinction for main diagonal panels (where the metallicity of the used grid is the same as the true metallicity) as well as for out-of-diagonal panels (where the metallicities are different).

In the latter case, the similar metallicity effects are seen as in Section 2.4, producing offsets on the age and mass, and increasing the scatter in the extinction.

## 2.6.2 One-metallicity vs whole metallicity range: taking metallicity effects into account

In this test we derive the age, mass, extinction, and metallicity of the same artificial clusters of fixed metallicity, but here using a model grid containing 13 metallicities (from [M/H] = 0.2 to -2.2) in order to check the ability of the method to constrain the metallicity too. We studied the clusters allowing three different amounts of photometric errors in order to study their influence on the derivation of parameters: Gaussian photometric errors of σ = 0.03, 0.05, and 0.1 mag were added to each magnitude. Fig. 2.16 shows the results; the block of panels (b) can be compared to the results shown in Fig. 2.13, as the same amount of photometric error has been added to artificial cluster photometry. The presence of the ultraviolet F275W passband of the WFC3 photometric system is important as it helps to significantly reduce the biases in parameter derivation, including metallicity, compared to the U BV RI photometric system.

Concerning the amount of photometric errors, in Fig. 2.16 we see a much larger agreement between derived and true parameters for low and medium amount of added photometric errors. When the photometric errors reach 0.1 mag, the scatter around true age and extinction is strongly increased. Also, the metallicity of artificial clusters with the true metallicity [M/H] = -0.6 is well derived only when the photometric accuracy is no larger than 0.05 mag. The better the photometric accuracy, the higher the accuracy of the derived metallicity can be achieved with the WFC3 passbands what is emphasized in the Section 3.2 by use of real data. kpc. This subsample consists of 216 clusters and is displayed in Fig. 3.2. It is studied with our method described in Section 2.1, using the Milky Way standard extinction law (Cardelli et al. 1989) and distance modulus to M31 of (m -M ) 0 = 24.47 derived by McConnachie et al. (2005).   2009) results. The second column (panels b, e, h) compares the age, mass, and extinction derived when a wide extinction range is allowed vs the Vansevičius et al. (2009) results. The last column (panels c, f, i) compares the results obtained with a wide extinction range allowed vs the ones obtained with a narrow extinction range allowed.

In Fig. 3.3 (a), when clusters are studied in a narrow allowed extinction range, E(B -V ) = [0.04, 0.5], the derived ages show the same features as the models studied in Fig. 2.5 (d), reproduced here in the background of the panel. The degeneracy streaks develop above and below the one-to-one line, perpendicularly to it, and are marked by ellipses numbered "1" and "2" in Fig. 3.3 (a). As for the models in the background, the upper degeneracy streak concerns clusters with overestimated age and underestimated extinction, shown by ellipse "1" in Fig. 3.3 (g). In contrast, for the lower degeneracy streak (ellipse "2"), the age is underestimated and extinction is overestimated. Since the upper streak (ellipse "1") is more developed than the lower one ("2"), we interpret that as a result of a too narrow extinction range in the model grid allowed, E(B -V ) = [0.04, 0.5]. If the intrinsic range of extinction for a cluster sample is wide, as in the galaxy M31, then a narrow extinction range of models produces an extended upper streak (ellipse "1") and a smaller lower streak (ellipse "2"), shown in Fig. 3.3 (a). In panel (b), when the allowed extinction range of models is wide, the upper streak retracts and the lower streak develops. We conclude that in a galaxy with wide extinction range, it is not possible to derive the parameters for the clusters affected by age-extinction degeneracy and additional constraints for the extinction are needed; e.g., Vansevičius et al. (2009) used a Spitzer emission map, to trace the dust lanes of M31 and to reduce the age-extinction degeneracy. Figs. 3.3 (d,e) show that for high-mass clusters we obtain lower masses than those given by Vansevičius et al. (2009). Inspecting the metallicity values provided by Vansevičius et al. (2009), we note that high-mass clusters have metallicities lower than the [M/H] = -0.4 used in our model grid.  This could be a sign of the metallicity effect on the derivation of physical parameters.

## 3.2 The M31 galaxy star cluster sample of PHAT survey

Using the WFC3+ACS photometric system on board HST, the Panchromatic Hubble Andromeda Treasury (PHAT) team (see, e.g., Dalcanton et al. 2012;Beerman et al. 2012;Weisz et al. 2013) performed a survey of 1/3 of the M31 galaxy (the north-east region), providing a large catalog of 601 clusters (Johnson et al. 2012), shown in Fig. 3.1. This catalog of star clusters was already analyzed by Fouesneau et al. (2014), who derived their age, mass, and extinction. They used a constant solar metallicity through the whole M31 disk, arguing that the HII zone study (Zurita & Bresolin 2012) does not show any significant metallicity gradient. They allowed four different metallicities ([M/H] = -0.7, -0.4, 0.0, and +0.4, i.e., from Small Magellanic Cloud to super-solar metallicities) for 30 massive globular-like clusters with mass > 10 5 M ⊙ .

We first selected a sample of 402 clusters from the catalog of Johnson et al. (2012) with available magnitudes in all photometric passbands. Then from this sample we selected two cluster groups, for which we display the photometric accuracy for each passband in Fig. 3.4. In cluster group 1 (65 objects, the large filled dots in Fig. 3.4), the photometric accuracy of objects is < 0.15 mag in F275W and F336W, < 0.1 mag in F475W and F814W, and < 0.2 mag in F110W and F160W. In cluster group 2 (138 objects, the large open dots in Fig. 3.4), the photometric accuracy in each passband is < 0.5 mag. In total, we analyze 203 clusters. In Fig. 3.4 we indicate for each passband the number of objects from the 203 clusters for which photometry is more accurate than 0.03, 0.05, 0.1 mag.

We derived the parameters of both cluster groups by firstly fixing the metallicity of all clusters to the solar value, and a second time by allowing a large range of metallicities in the model grid with 13 values of [M/H] = +0.2 to -2.2, in steps of 0.2.

The color-color diagrams of cluster groups 1 and 2 are shown in Fig. 3  we see that the SSPs are rather close, while this is not the case anymore in panel b), where UV and IR passbands are shown. This indicates that, at least for massive and old clusters (center to bottom of panel b), the derivation of metallicity is possible with the WFC3+ACS system, provided that the photometric accuracy is reasonable, such as for group 1 clusters (for which the maximum photometric accuracy is indicated in Fig. 3.5).

## 3.2.1 Results with fixed solar metallicity

The age, mass, and extinction derived with the fixed metallicity grid  newegen & de Jong (1993) for the TP-AGB phase, while PADOVA stellar models used here attempt to numerically reproduce the physics of that stellar phase (see Marigo et al. 2008;Girardi et al. 2010). For the masses, Fouesneau et al. (2014) provide the present-day mass, while the masses output by our method are initial masses, causing a natural slight shift be-  tween their mass predictions and our mass predictions. The four clusters of group 1 (Fig. 3.6b; filled points) strongly below the identity line and classified as massive by Fouesneau et al. (2014) are in fact globular-like clusters1 , wrongly classified by our method when the metallicity is fixed to the solar value in the model grid. We provide more details on them in the following sections.

## 3.2.2 Results with free metallicity

Parameters derived when metallicity is left free are shown in Fig. 3.7. As expected from artificial tests, the introduction of the free metallicity parameter introduces a new level of complexity. Here we compare the age, mass, and extinction derived when metallicity is left free versus the same parameters when the metallicity is fixed to the solar value.

Many clusters seen as young or middle-aged in metal-fixed case are now seen as older. For example, the five points in the top left corner of the age panel (Fig. 3.7 a, four of which are the filled points below the identity line in Fig. 3.6 b) are seen as young in the case where metallicity is fixed to solar value, but old in the case where metallicity is left free. They are also more massive, located well above the identity line in the mass panel Fig. 3.7 (b). These five objects are classified as of low-metallicity when the metallicity is left free, which is also found likely when inspecting the images, as they are brighter in the F275W and F336W passbands than other globular-like clusters classified with higher metallicity. We used the individual cluster pictures in the six WFC3+ACS passbands and also Sloan Digital Sky Survey (SDSS), Two Micron All Sky Survey (2MASS), and Galaxy Evolution Explorer (GALEX) images available through ALADIN 2 Sky Altas to confirm that these objects are really globular-like clusters, and not young low-mass clusters. These five objects, with given PHAT ID 1439, 428, 680, 683, and1396, are also confirmed as globular clusters in the Revised Bologna Catalog (2012, version 5, see also Galleti et al. 2004) with the designation B064D-NB6, B229-G282, B165-G218, B167-G212, and NB21-AU5, indicated from 1 to 5 respectively in the Figs. 3.6, 3.7, and 3.8.

2 http://aladin.u-strasbg.fr/ As an illustration, 2-dimensional marginalized likelihood maps are shown for one of these objects, ID 428 (indicated as "2" in the Figs. 3.6, 3.7, and 3.8), in Fig. 3.9. The likelihood maps are given for the cluster classification using all 13 metallicities of the model grid. The parameters derived taking the maximum of likelihood L node (see Eq. 2.2) in the 4-dimensional model grid are indicated with the white points in the 2dimensional marginalized likelihood maps. Additionally, the black dots indicate the parameters obtained when the metallicity is fixed to the solar value in the model grid (hence reduced to a 3-dimensional grid), resulting in a wrongly classified younger, lower-mass, and much more extincted solution. For this object, ID 428, Fouesneau et al. (2014) as well as our results

when metallicity is fixed to solar value give a too young age and a too low mass. Our results derived with free metallicity show that this object is an old massive globular-like cluster, and visual inspection of the HST images shown in Fig. 3.10 through the ALADIN Sky Atlas confirms clearly that this object is a globular-like cluster.

We note that in Fig. 3.7 (a) a dozen of the objects with ages, derived adopting a fixed solar metallicity, around log 10 (t/yr) = 8, have overestimated ages when derived with free metallicities. This is very likely because these objects are relatively faint, with poor photometric accuracy, and are contaminated by bright red background stars. However, a careful analysis of the WFC3+ACS object images and their likelihood maps (similar to those shown in Fig. 3.9) allows us to resolve degeneracies in most of the cases.

Recently, Caldwell et al. (2011) produced the spectroscopic study of old star clusters of M31 galaxy, using the Lick indices to derive their age, mass, extinction, and metallicity. To check the reliability of our derived metallicity, we compare those of the 36 clusters common to the Caldwell et al. (2011) sample and the clusters analyzed in this study in Fig. 3.8. As Caldwell et al. (2011) fixed the age of most of the clusters to 14 Gyr, The derived metallicity of clusters with ages lower than 1 Gyr (panel a), and of clusters with ages higher than 1 Gyr (panel b) for group 1 (thick line) and group 2 (thin line).

here we only compare the mass and metallicity of the clusters. Again, an overall agreement is found between the parameters. The accuracy of our photometric metallicity derivation is linked to the mass, and thus very likely to the signal-to-noise of available photometry for each object, as the scatter seen in Fig. 3.8 (c) is increasing with decreasing star cluster mass. The five clusters studied above are also indicated in Fig. 3.8, where one can see that the metallicity derived using our method coincides well with that of the spectroscopic method of Caldwell et al. (2011).

In Fig. 3.11, we show the histograms of derived metallicity for young age clusters (log 10 (t/yr) < 9, panel a) and old age clusters (log 10 (t/yr) ⩾ 9, panel b) of group 1 (thick line) and group 2 (thin line). Most of the young clusters are classified as metal-rich, while the old cluster metallicities are more dispersed. Note, that even for low photometric accuracy,

## 3.3 Application to the M33 star clusters

## 3.3.1 Why M33?

There is a current need for an accurate catalog for the star cluster system of the Triangulum galaxy, or Messier 33 (M33), as it could be used as a constraint on the derivation of star formation history in this galaxy. Several other reasons encourage the study of this particular star cluster system. The nearly face-on inclination (i = 56 degrees, Regan & Vogel 1994)

##  of M33

reduces extinction effects for the majority of its cluster population, situated in the disk. Also, M33 is the only close late-type spiral galaxy, situated at a distance of 867 kpc (Galleti et al. 2004, distance modulus of (m -M ) 0 = 24.69), making its star cluster system accessible to ground-based telescopes for integrated photometric and spectroscopic studies and to the Hubble Space Telescope (HST) for resolved measurements. While other star cluster systems of the Local Group galaxies have received considerable attention, as in the case of M31 and the Magellanic Clouds, the M33 star cluster system has not been studied as much. Therefore, an extended knowledge of its star cluster system would improve the understanding of the relationship between star clusters and their host galaxies. The M33 star cluster system has nevertheless been studied for a long time. Several teams (Hiltner 1960;Kron & Mayall 1960;Melnick & D'Odorico 1978;Christian & Schommer 1982, 1988;Mochejska et al. 1998) contributed to the building of a catalog of star clusters in M33 using ground-based unresolved photometry in optical passbands. Chandar et al. (1999aChandar et al. ( ,b,c, 2001) ) used the WFPC2 camera onboard HST to detect 102 additional clusters. They derived their physical parameters using integrated photometry that were compared with SSP models, which are ideal star cluster models in the sense that they are based on a continuously sampled IMF (see Chapter 1). Sarajedini et al. (1998Sarajedini et al. ( , 2000Sarajedini et al. ( , 2007) ) also used WFPC2 and ACS images, but derived the parameters using resolved color-magnitude diagrams for the most massive clusters. All studies before 2007 have been combined in a merged catalog by Sarajedini & Mancone (2007)   (2014) shown as open red circles, Ma (2012Ma ( , 2013) ) as open blue squares, San Roman et al. (2010) as green diamonds, San Roman et al. (2009) as violet crosses. The three dashed ellipses have semimajor axes of 10 ′ , 20 ′ , and 30 ′ to the center (marked as a large black plus symbol) and can be seen as circles of the same radii projected on the M33 disk. and metallicity). However, as presented in Sections 1.1 and 1.2, it is know well known that these models are oversimplified and biased, as they do not take the natural dispersion of integrated colors of star clusters into account, the stochasticity problem. In this Section, we aim to study the M33 star cluster system with the star cluster models that takes the stochasticity problem into account.

## 3.3.2 The M33 star cluster catalog

Recently San Roman et al. (2010) observed 803 M33 star clusters (599 candidates and 204 confirmed using the HST) using the 3.6 m Canada-France-Hawaii-Telescope (CFHT) and published a catalog in the MegaCam camera u * g ′ r ′ i ′ z ′ photometric system. Although their catalog also contained the cluster photometry converted to the ugriz photometric system of the Sloan Digital Sky Survey (SDSS), we considered here the native MegaCam photometric system to avoid likely conversion approximation.

Using archival images of the Local Group Galaxies Survey (LGGS, Massey et al. 2006)   (2012,2013) is shown in Fig. 3.13. We adopted for the U BV RI photometric system the Ma (2012Ma ( , 2013) ) photometry when available, and the Fan & de Grijs (2014) photometry for other clusters, correcting the Fan & de Grijs (2014) photometric zero-points to the Ma (2012Ma ( , 2013) ) ones in order to have a homogeneous catalog. The zero-point correction coefficients were, for Fan & de Grijs (2014) minus Ma (2012Ma ( , 2013) ) photometry: ∆V = -0.099 mag,  Ma (2012Ma ( , 2013) ) catalogs.

These catalogs include all objects published in the catalog of star clusters of Sarajedini & Mancone (2007), who merged all the M33 star cluster catalogs published before 2007. The association of these catalogs in this paper results in a merged catalog of 910 objects, which is shown in Fig. 3.12 color-coded to show to which original catalog the clusters belong.

We supplemented optical data with near-infrared data by using deep Two Micron All Sky Survey (2MASS) JHK images3 with exposure times 6 times longer (2MASS 6X) than the standard 2MASS ones. This results in a photometry approximatively 1.5 mag deeper in 2MASS 6X than photometry derived from standard 2MASS images. The photometry of clusters was obtained by the use of aperture photometry using the standard IRAF/digiphot/apphot package with an aperture radius in the range 2 ′′ to 4 ′′ , and an aperture correction built using the curves of growth of a dozen relatively isolated clusters. By this process, we derived the JHK photometry of 758 clusters. To ensure that the 2MASS 6X images were correctly calibrated, we also derived aperture photometry of stars, selected in the same region where clusters are located, and compared this derived aperture photometry to the stellar aperture photometry provided by the 2MASS  We also add ultraviolet aperture photometry from GALEX5 by using aperture radii of 3 ′′ in both far-ultraviolet (FUV) and near-ultraviolet (NUV) passbands. This photometry was not used to derive the star cluster parameters, but only for the qualitative confirmation of the results in the case of young clusters, as ultraviolet magnitudes fade very quickly with age, becoming too faint at the distance of M33 after ≳100 Myr. Also, the very wide Point Spread Function (PSF) of the GALEX telescope makes the accurate derivation of UV colors impossible for all clusters, but only for the few relatively isolated ones (at least at a distance of two aperture radii from any other UV-emission in the worst cases). Fig. 3.15 presents the multi-passband photometric data in different colorcolor diagrams in optical cases (U BV RI and u * g ′ r ′ i ′ z ′ ). Fig. 3.16 shows the clusters in the GALEX photometry (top panels) only for objects undisturbed by close neighboring UV emission, and in deep 2MASS 6X photometry (bottom panels). The clusters are shown with SSP models (solid lines) and also with a grid of artificial star cluster models which take the stochastic dispersion of their colors into account, as described in Section 1.4.

Both SSP and stochastic model grid are shown with the same metallicity,

Although GALEX photometry is inaccurate for most of the 910 objects, because of the presence of possible UV emitting neighboring objects, we  scope and 24 µm image from the Spitzer6 telescope. We created multipassband images for each cluster in our catalog that were used to visually confirm the results of our method of star cluster parameter derivation. In After the rejection of the 95 stars from the 910 objects sample as well as a few clusters with incomplete photometry, 747 clusters remain to be studied.

## 3.3.3 Artificial tests

The ability of the method to derive star cluster parameters has already been evaluated in Sections 2.3, 2.4, 2.5, and 2.6. Here we are interested in seeing for which conditions the method would be sensitive enough to detect a change in slope in the number of clusters per age bin distribution (hereafter referred to as differential age distribution) of the cluster sample such as shown by the solid line in Fig. 3.22 (d). Indeed, a two-slope profile in the differential age distribution could be interpreted as a decrease in the number of clusters due to an evolutionary fading of the cluster magnitudes (first slope) and a decrease in the number of clusters due to their disruption (second slope), as is discussed in greater details in Section 3.3.4. Here, the objective is to model an artificial star cluster population with such a twoslope profile in the true differential age distribution and to see whether the derived differential age distribution reproduces this profile depending on which photometric system we use.

We generated a sample of 10 000 artificial star clusters. The differential age distribution of the artificial clusters was chosen to mimic a two-slope profile similar to that described in Vansevičius et al. (2009) for M31 star clusters (see their Fig. 5a, reproduced in our Fig. 3.22 (d) in solid line).

For simplicity, the mass of the clusters was fixed to log 10 (M /M ⊙ ) = 4, a typical value for the clusters observed in M33. The extinction was randomly generated uniformly in the range E(B -V ) = 0 to 1.  formed for three combinations of photometric systems: optical (U BV RI), optical with near-infrared (U BV RI + JHK) and ultraviolet with optical (GALEX + U BV RI). The U BV RI system is used as a reference for the mass derivation, so it has been used in magnitudes in Eq. 2.1. For the other passbands, we have used colors instead, FUV-NUV for the GALEX passbands and J -H, J -K, and H -K for the 2MASS ones. This allows us to combine different catalogs of clusters built using slightly different aperture sizes: we use the magnitudes for one catalog, and the colors for the others. However, it is important that for each cluster at least one magnitude should be given, not just colors, so that the mass of the clusters could be estimated reliably by the method.

We added photometric uncertainties as a Gaussian noise with standard deviations of 0.05 mag for each U BV RI photometric passbands, 0.1 mag for JHK, and 0.15 mag for GALEX FUV and NUV.

In can be rather misleading when using U BV RI photometry alone. Indeed the direct comparison of the true and derived ages of the individual clusters in panel (a) shows that the agreement is far from being evident, especially at old ages, where the true metallicity of artificial clusters and the fixed one of the model grid ([M/H] = -0.4) deviate most. As a natural consequence, most of the clusters with true age above log 10 (t/yr) = 9.5 have age underestimated. Also, the presence of the natural age-extinction degeneracy in the optical U BV RI case, already discussed in Sections 2.3, 2.4, and 2.5, produces the streaks developing perpendicularly to the left and to the right of the diagonal identity dashed line, in Fig. 3.22 (a). The situation is less ex-treme, but still strongly affected by these degeneracies when we add JHK passbands to U BV RI ones (second row of panels). When we use GALEX with U BV RI passbands (third row of panels), the age-extinction degeneracy disappears, but the deviation from the identity line occurs because of the strong sensitivity of the ultraviolet to metallicity. Bianchi (2011) indeed shows by use of integrated spectra of SSP models that it is in the ultraviolet spectral region that the spectra are most affected by a change in metallicity.

We performed a second test, fixing the metallicity to [M/H] = -0.4 for all clusters, and then, only for clusters which have derived age larger than log 10 (t/yr) = 9, we re-derive a solution leaving the metallicity free to vary in the range [+0.2, -2.2]. Indeed, one notices in the first test that the situation was most complicated for clusters with true age above 1 Gyr. The results, shown in Fig. 3.23, still suffer from strong age-extinction degeneracy in the case of U BV RI passbands only (first row of panels). The inclusion of nearinfrared photometry improves much the derivation as the streaks developing perpendicularly to the identity line in Fig. 3.23 (e) are strongly reduced. In this case, the match between the true and derived age distributions in panels (g) and (h) is much more secure for all age ranges. When using GALEX with U BV RI (third row of panels), a gap is visible in panel (i) due to the strong sensitivity of the ultraviolet flux to metallicity. In this case, strong biases are still present in the age distribution (Fig. 3.23k and Fig. 3

##  .23l).

A third test was performed in which the metallicity of the model grid was left free in the whole age range, and the results are presented in Fig. 3.24.

Here we see that the use of optical passbands only (first row of panels) or even optical with near-infrared (second row) can lead to strong biases as these photometric systems are not sensitive enough to discriminate between models of different metallicities (see also Sections 2.4 and 2.5 for the sensitivity of the derived parameters on the metallicity, as well as for the derivation of the metallicity parameter). As a consequence, age distributions (panels c and d for the U BV RI case, panels g and h for the U BV RI + JHK case) are strongly affected. Only ultraviolet associated with optical data passbands are able to break the age-extinction degeneracies when the metallicity is left free, as shown in last row of panels. As a consequence, the derivation of the correct two-slopes profile in the differential age distribution is best done using GALEX + U BV RI when metallicity is left free, see Fig. 3.24l).

## 3.3.4 The derived physical parameters of the M33 star clusters

We applied the method of derivation of physical parameters to the sample of 747 M33 clusters using the optical U BV RI and near-infrared JHK passbands. We first fix the metallicity to [M/H] = -0.4 for all clusters, and then, only for clusters which have derived age larger than log 10 (t/yr) = 9, we re-derive a solution leaving the metallicity free to vary in the range [+0.2, -2.2], as it was shown to be the best choice for this passband combination in previous section.

As it has been done for artificial tests, we used the U BV RI system as a reference for the mass derivation, so it has been used in magnitudes in Eq. 2.1. For the other passbands used, u * g ′ r ′ i ′ z ′ and JHK, we have used colors instead, to avoid problems of different apertures in the different catalogs used. The colors used were u * -g ′ , g ′ -r ′ , g ′ -i ′ , r ′ -i ′ , and i ′ -z ′ for the CFHT passbands, and J -H, J -K, and H -K for the 2MASS passbands.

We used the extinction law of Gordon et al. (2003) derived for the LMC, assuming that for a similar metallic content the M33 galaxy would have a similar extinction law. The minimum extinction of clusters has been set to E(B -V ) = 0.04 mag, the value of the foreground extinction in the direction of M33 estimated from the Schlegel et al. (1998) extinction maps.

The results for the age and mass obtained here are compared in Fig. 3.25 with those of 160 San Roman et al. (2009), obtained by isochrone fitting on HST-resolved color-magnitude diagrams. In the case of the San Roman et al. (2009), cluster ages are enclosed in a much narrower range, mainly between 50 Myr and 1 Gyr. Although our age distribution is wider than in their case, a satisfactory agreement is found between both sets of results, as well as for the mass parameter.

Globular-like clusters (red circles, visually confirmed as globular clusters on HST images) are found to be very old in our case, and more massive. San Roman et al. (2009) noted that the lack of clusters with ages  dar et al. (2002) give log 10 (t/yr) = 10.08 (12 Gyr in their table 5) using the spectroscopic line index models of Worthey (1994). For MKKSS12, we  (2002) give log 10 (t/yr) = 9.4 using SSP models, and Ma et al. (2004) give log 10 (t/yr) = 9.63 and log 10 (M /M ⊙ ) = 5.47 using their BATC spectrophotometric system composed of 13 narrow passbands, also compared to SSP models.

For young clusters, the age given by San Roman et al. (2009) is often larger than our values. In Fig. 3.25 (a,c) we note that the two white circles, which are for the clusters still within HII zones and so very young, are also seen as older in San Roman et al. (2009) than in our study. Also, many clusters that are bright in UV (blue circles) are also older in San Roman et al. (2009) than in our case. However, UV brightness fades very quickly, becoming faint at the distance of M33 after ≳100 Myr, making it unlikely that the age of these clusters is older.   & Mancone (2007) seem to be artifacts due to the SSP method, as is the case for the SSP derived ages in Fig. 3 of Fouesneau & Lançon (2010). Popescu et al. (2012) show the same features, this time for real clusters.

They derived the age of LMC star clusters using the stochastic method and compared these values to the ages derived by Hunter et al. (2003) using the SSP method. The comparison, shown in Fig. 8 of Popescu et al. (2012) (the order of the x-and y-axes is flipped compared to our figure), shows similar features to the Fouesneau & Lançon (2010) study and to this work: the deviations from the identity line are attributed to artefacts of the SSP method of parameter derivation. As our merged cluster sample also contains the HST detected objects from San Roman et al. (2009), some clusters may be found well below this limit.  2009) also used the data of Rosolowsky & Simon (2008) to derive the E(B -V ) values for 58 HII regions, and show in their Fig. 9 that the extinction can be expected to be E(B -V ) ≲ 0.3 mag for those regions (except for 3 objects), with an average of E(B -V ) ∼ 0.11 mag.

In Fig. 3.27 (f) is shown the extinction of all clusters depending on their deprojected galactocentric distance (assuming that all clusters are in the disk, which is incorrect for globular-like clusters). The global median extinction is 0.16 mag. The extinction that we found is generally higher for young clusters than for old ones, as shown in Fig. 3.27 (b). Indeed, the majority of clusters still embedded or close to HII zones (white circles) are found more extincted with a median of 0.34 mag. The clusters bright in UV (blue circles) have a median extinction of 0.17 mag, while the clusters faint in UV (cyan circles) have a lower median extinction of 0.14 mag.

The globular-like clusters (red circles) have the smallest median extinction, 0.09 mag. Fig. 3.28 describes the age and mass distributions (panels a and b), and the differential age and mass distributions (panels c and d). We see that the differential age distribution is composed of a two-slope profile. Boutloukos & Lamers (2003) and Lamers et al. (2005) interpreted the first slope as a natural magnitude fading due to stellar evolution, and the second slope as due to cluster disruption mechanisms such as the galaxy tidal field effect or encounters with giant molecular clouds. Hence we see here that the cluster sample is dominated by the magnitude fading until log 10 (t/yr) ∼ 8.5 and that after the cluster disruption phase takes over. This typical lifetime scale is comparable to the one derived for the star cluster population in the south-west field of the M31 galaxy by Vansevičius et al. (2009) using a star cluster sample photometry from Narbutis et al. (2008).  Following Gieles (2009), we compare the cluster differential mass distribution to the Schechter (1976)

##  Conclusions

In this work, we aimed to tackle the two major problems faced when deriving the physical parameters (age, mass, extinction, and metallicity) of unresolved star clusters, that are the problems of the degeneracy between the star cluster parameters, and the stochastic dispersion of observed cluster colors due to the stochastic sampling of massive stars.

In Chapter 1, the problems of degeneracy and stochasticity have been introduced for unresolved star clusters with integrated broad-band photometry. It has been shown that the Simple Stellar Population models are unfit to derive the cluster parameters. Then the stellar mass random sampling method that allows us to model the stochasticity in star clusters has been presented, as well as the model grid built for all physical parameters of star clusters.

In Chapter 2, the method to derive the star cluster physical parameters has been developed taking into account the stochasticity problem. The method has been tested on several artificial cluster samples in the cases where the extinction and metallicity are known or unknown, to show the degeneracies linked to these parameters. By use of different photometric system combinations, U BV RI, U BV RI + JHK, GALEX+U BV RI, and WFC3, it has been demonstrated that the ultraviolet combined with optical is best suited for the break of degeneracies between clusters parameters. The impact of photometric errors has also been studied for the particular case of the WFC3 photometric system.

In Chapter 3, the method of cluster parameter derivation has been applied on real star cluster samples from two major Local Group galaxies, M31 and M33. For M31 clusters, the age-extinction degeneracy has been explored using a star cluster sample of Vansevičius et al. (2009) based on ground-based U BV RI photometry, and the age-metallicity degeneracy has been explored using a star cluster sample of PHAT survey (Johnson et al. 2012), observed in the WFC3 photometric system onboard the Hubble Space Telescope. In the latter case we derived the cluster parameters, including the metallicity, and hence showed the metallicity effects on the parameter derivation accuracy. For the clusters in common to the Caldwell et al. (2011) spectroscopic study, we compared the metallicity with their values and found and overall agreement. This demonstrated by use of the sample of real star clusters that the WFC3 photometric system is suitable to evaluate the star cluster parameters when the metallicity is unknown, and evaluates the metallicity when the signal-to-noise is high enough.

Finally, we studied the star cluster system of the M33 galaxy, using the most recent optical broad-band photometry catalogs, and supplemented near-infrared measurements using deep 2MASS images. We presented the derivation of the age, mass, and extinction of the clusters for a metallicity fixed to [M/H] = -0.4 (LMC-like), and, in the case when the age derived is larger than 1 Gyr, a new solution was derived using free metallicity in the range [+0.2, -2.2].

We ensured, by use of artificial clusters, that the star cluster physical parameter derivation method can reproduce correctly a given two-slope profile in the differential age distribution, testing it for different photometric systems: optical alone (U BV RI), optical combined with near-infrared (U BV RI + JHK), and ultraviolet with optical (GALEX + U BV RI). We showed that the optical with near-infrared case is suitable for the correct derivation of the two-slope profile and used it for the M33 star cluster system.

A two-slope profile of differential age distribution found for the M33 star cluster system has been interpreted as: the typical lifetime before disruption of star clusters in M33 is found to be ∼ 300 Myr, comparable to what is found for M31 star clusters. We showed that the differential mass distribution of clusters is consistent with a Schechter (1976) function with a power-law index of β = 2 and a characteristic mass of M * = 2 × 10 5 M ⊙ .

To conclude, we have demonstrated in this thesis, by use of artificial tests as well as real star clusters, that stochastic modeling of star clusters is best fitted to derive their parameters, as well as to derive the essential properties of star cluster populations in other galaxies.

## References

[1] Analysing observed star cluster SEDs with evolutionary synthesis models: systematic uncertainties
		PAnders
		NBissantz
		UFritze-V. Alvensleben
		RDe Grijs
		10.1111/j.1365-2966.2004.07197.x
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		347
			1
			
			2004
			Oxford University Press (OUP)

[2] RAndrae
		2010
	ArXiv e-prints

[3] CBarbaro
		CBertelli
	A&A
		54
			243
			1977

[4] THE PANCHROMATIC HUBBLE ANDROMEDA TREASURY. III. MEASURING AGES AND MASSES OF PARTIALLY RESOLVED STELLAR CLUSTERS
		LoriCBeerman
		LCliftonJohnson
		MorganFouesneau
		JulianneJDalcanton
		DanielRWeisz
		AnilCSeth
		BenFWilliams
		EricFBell
		LucianaCBianchi
		NelsonCaldwell
		AndrewEDolphin
		DimitriosAGouliermis
		JasonSKalirai
		SørenSLarsen
		JasonLMelbourne
		Hans-WalterRix
		EvanDSkillman
		10.1088/0004-637x/760/2/104
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		760
			2
			104
			2012
			American Astronomical Society

[5] GBertelli
		ABressan
		CChiosi
	A&AS
		106
			275
			1994

[6] GALEX and star formation
		LucianaBianchi
		10.1007/s10509-011-0612-2
	Astrophysics and Space Science
		Astrophys Space Sci
		0004-640X
		1572-946X
		335
			1
			
			2011
			Springer Science and Business Media LLC

[7] Star cluster formation and disruption time-scales - I. An empirical determination of the disruption time of star clusters in four galaxies
		SGBoutloukos
		HJ G L MLamers
		10.1046/j.1365-8711.2003.06083.x
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		338
			3
			
			2003
			Oxford University Press (OUP)

[8] ABridžius
		DNarbutis
		RStonkutė
	Baltic Astronomy
		17
			337
			2008

[9] STAR CLUSTERS IN M31. I. A CATALOG AND A STUDY OF THE YOUNG CLUSTERS
		NelsonCaldwell
		PaulHarding
		HeatherMorrison
		JamesARose
		RicardoSchiavon
		JeffKriessler
		10.1088/0004-6256/137/1/94
	The Astronomical Journal
		The Astronomical Journal
		0004-6256
		1538-3881
		137
			1
			
			2009
			American Astronomical Society

[10] STAR CLUSTERS IN M31. II. OLD CLUSTER METALLICITIES AND AGES FROM HECTOSPEC DATA
		NelsonCaldwell
		RicardoSchiavon
		HeatherMorrison
		JamesARose
		PaulHarding
		10.1088/0004-6256/141/2/61
	The Astronomical Journal
		The Astronomical Journal
		0004-6256
		1538-3881
		141
			2
			61
			2011
			American Astronomical Society

[11] The relationship between infrared, optical, and ultraviolet extinction
		JasonACardelli
		GeoffreyCClayton
		JohnSMathis
		10.1086/167900
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		345
			245
			1989
			American Astronomical Society

[12] Confidence limits of evolutionary synthesis models
		MCerviño
		VLuridiana
		10.1051/0004-6361:20053283
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		451
			2
			
			2004. 2006
			EDP Sciences
	A&A

[13] Confidence levels of evolutionary synthesis models
		MCerviño
		DValls-Gabaud
		VLuridiana
		JMMas-Hesse
		10.1051/0004-6361:20011266
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		381
			1
			
			2002
			EDP Sciences

[14] Star Clusters in M33. II. Global Properties
		RupaliChandar
		LucianaBianchi
		HollandCFord
		10.1086/307228
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		517
			2
			
			1999a, ApJS, 122, 431 -. 1999b. 2001
			American Astronomical Society
	A&A

[15] Kinematics of Star Clusters in M33: Distinct Populations
		RupaliChandar
		LucianaBianchi
		HollandCFord
		AtaSarajedini
		10.1086/324147
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		564
			2
			
			1999. 2002
			American Astronomical Society
	ApJ

[16] Models of Population Synthesis
		CesareChiosi
		GianpaoloBertelli
		AlessandroBressan
		10.1007/978-94-011-2434-8_42
	The Stellar Populations of Galaxies
		Springer Netherlands
			1988
			196

[17] The cluster system of M33
		CAChristian
		RASchommer
		10.1086/190804
	The Astrophysical Journal Supplement Series
		ApJS
		0067-0049
		1538-4365
		49
			405
			1982. 1988
			American Astronomical Society
	AJ

[18] SLUG—STOCHASTICALLY LIGHTING UP GALAXIES. I. METHODS AND VALIDATING TESTS
		RobertLDa Silva
		MicheleFumagalli
		MarkKrumholz
		10.1088/0004-637x/745/2/145
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		745
			2
			145
			2012
			American Astronomical Society

[19] THE PANCHROMATIC HUBBLE ANDROMEDA TREASURY
		JulianneJDalcanton
		BenjaminFWilliams
		DustinLang
		TodRLauer
		JasonSKalirai
		AnilCSeth
		AndrewDolphin
		PhilipRosenfield
		DanielRWeisz
		EricFBell
		LucianaCBianchi
		MarthaLBoyer
		NelsonCaldwell
		HuiDong
		ClaireEDorman
		KarolineMGilbert
		LéoGirardi
		StephanieMGogarten
		KarlDGordon
		PuragraGuhathakurta
		PaulWHodge
		JonAHoltzman
		LCliftonJohnson
		SørenSLarsen
		AlexiaLewis
		JasonLMelbourne
		KnutA GOlsen
		Hans-WalterRix
		KeithRosema
		AbhijitSaha
		AtaSarajedini
		EvanDSkillman
		KrzysztofZStanek
		10.1088/0067-0049/200/2/18
	The Astrophysical Journal Supplement Series
		ApJS
		0067-0049
		1538-4365
		200
			2
			18
			2012
			American Astronomical Society

[20] Deriving physical parameters of unresolved star clusters
		PDe Meulenaer
		DNarbutis
		TMineikis
		VVansevičius
		10.1051/0004-6361/201220674
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		550
			A20
			2013
			EDP Sciences
			Baltic Astronomy
	Paper I -. 2014a, A&A, 569, A4, Paper II -. 2014b

[21] Table 1: Sociodemographic Characteristics (Baranyi et al., 2015a; Baranyi et al., 2015b; Baranyi et al., 2016).
		10.7717/peerj.3968/table-1
		null
			PeerJ
			574
	Paper III -. 2015b, ArXiv e-prints. Paper IV

[22] Discussion on the Paper by Professor Dempster, Professor Laird and Dr Rubin
		APDempster
		NMLaird
		DBRubin
		10.1111/j.2517-6161.1977.tb01601.x
	Journal of the Royal Statistical Society Series B: Statistical Methodology
		1369-7412
		1467-9868
		39
			1
			
			1977
			Oxford University Press (OUP)

[23] VDeveikis
		DNarbutis
		RStonkutė
	Baltic Astronomy
		17
			351
			2008

[24] FanZDe Grijs
		R
	ApJS
		211
			22
			2014

[25] MFioc
		BRocca-Volmerange
	A&A
		326
			950
			1997. 1999
	ArXiv Astrophysics e-prints

[26] THE PANCHROMATIC HUBBLE ANDROMEDA TREASURY. V. AGES AND MASSES OF THE YEAR 1 STELLAR CLUSTERS
		MorganFouesneau
		LCliftonJohnson
		DanielRWeisz
		JulianneJDalcanton
		EricFBell
		LucianaBianchi
		NelsonCaldwell
		DimitriosAGouliermis
		PuragraGuhathakurta
		JasonKalirai
		SørenSLarsen
		Hans-WalterRix
		AnilCSeth
		EvanDSkillman
		BenjaminFWilliams
		10.1088/0004-637x/786/2/117
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		786
			2
			117
			2014
			American Astronomical Society

[27] Accounting for stochastic fluctuations when analysing the integrated light of star clusters
		MFouesneau
		ALançon
		10.1051/0004-6361/201014084
	Astronomy and Astrophysics
		A&A
		0004-6361
		1432-0746
		521
			A22
			2010
			EDP Sciences

[28] The distance of M 33 and the stellar population in its outskirts
		SGalleti
		MBellazzini
		FRFerraro
		10.1051/0004-6361:20040489
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		423
			3
			
			2004
			EDP Sciences

[29] The early evolution of the star cluster mass function
		MGieles
		10.1111/j.1365-2966.2009.14473.x
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		394
			4
			
			2009
			Oxford University Press (OUP)

[30] The evolution of the V − K colours of single stellar populations
		LéoGirardi
		GianpaoloBertelli
		10.1046/j.1365-8711.1998.01934.x
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		300
			2
			
			1998
			Oxford University Press (OUP)

[31] THE ACS NEARBY GALAXY SURVEY TREASURY. IX. CONSTRAINING ASYMPTOTIC GIANT BRANCH EVOLUTION WITH OLD METAL-POOR GALAXIES
		LéoGirardi
		BenjaminFWilliams
		KarolineMGilbert
		PhilipRosenfield
		JulianneJDalcanton
		PaolaMarigo
		MarthaLBoyer
		AndrewDolphin
		DanielRWeisz
		JasonMelbourne
		KnutA GOlsen
		AnilCSeth
		EvanSkillman
		10.1088/0004-637x/724/2/1030
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		724
			2
			
			2010
			American Astronomical Society

[32] A Quantitative Comparison of the Small Magellanic Cloud, Large Magellanic Cloud, and Milky Way Ultraviolet to Near‐Infrared Extinction Curves
		KarlDGordon
		GeoffreyCClayton
		KAMisselt
		ArloULandolt
		MichaelJWolff
		10.1086/376774
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		594
			1
			
			2003
			American Astronomical Society

[33] Synthetic AGB Evolution in the LMC: The Abundances of PN
		MartinGroenewegen
		TeijeDe Jong
		10.1017/s0074180900172596
	Symposium - International Astronomical Union
		Symp. - Int. Astron. Union
		0074-1809
		155
			
			1993
			Cambridge University Press (CUP)

[34] Colors and Magnitudes of Clusters in M31 and M33.
		WAHiltner
		10.1086/146818
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		131
			163
			1960
			American Astronomical Society

[35] Cluster Mass Functions in the Large and Small Magellanic Clouds: Fading and Size-of-Sample Effects
		DeidreAHunter
		BruceGElmegreen
		TrentJDupuy
		MichaelMortonson
		10.1086/378056
	The Astronomical Journal
		AJ
		0004-6256
		1538-3881
		126
			4
			
			2003
			American Astronomical Society

[36] PHAT STELLAR CLUSTER SURVEY. I. YEAR 1 CATALOG AND INTEGRATED PHOTOMETRY
		LCliftonJohnson
		AnilCSeth
		JulianneJDalcanton
		NelsonCaldwell
		MorganFouesneau
		DimitriosAGouliermis
		PaulWHodge
		SørenSLarsen
		KnutA GOlsen
		IzaskunSan Roman
		AtaSarajedini
		DanielRWeisz
		BenjaminFWilliams
		LoriCBeerman
		LucianaBianchi
		AndrewEDolphin
		LéoGirardi
		PuragraGuhathakurta
		JasonKalirai
		DustinLang
		AntonelaMonachesi
		SanjayNanda
		Hans-WalterRix
		EvanDSkillman
		10.1088/0004-637x/752/2/95
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		752
			2
			95
			2012
			American Astronomical Society

[37] Better age estimation using ultraviolet–optical colours: breaking the age–metallicity degeneracy
		SKaviraj
		S-CRey
		RMRich
		S-JYoon
		SKYi
		10.1111/j.1745-3933.2007.00370.x
	Monthly Notices of the Royal Astronomical Society: Letters
		1745-3925
		1745-3933
		381
			1
			
			2007
			Oxford University Press (OUP)

[38] Photoeletric photometry of galactic and extragalactic star clusters.
		GEKron
		NUMayall
		10.1086/108306
	The Astronomical Journal
		0004-6256
		65
			581
			1960
			American Astronomical Society

[39] On the variation of the initial mass function
		PKroupa
		10.1046/j.1365-8711.2001.04022.x
	Monthly Notices of the Royal Astronomical Society
		Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		322
			2
			
			2001
			Oxford University Press (OUP)

[40] The Initial Mass Function of Stars: Evidence for Uniformity in Variable Systems
		PavelKroupa
		10.1126/science.1067524
	Science
		Science
		0036-8075
		1095-9203
		295
			5552
			
			2002
			American Association for the Advancement of Science (AAAS)

[41] Galactic‐Field Initial Mass Functions of Massive Stars
		PavelKroupa
		CarstenWeidner
		10.1086/379105
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		598
			2
			
			2003
			American Astronomical Society

[42] The Stellar and Sub-Stellar Initial Mass Function of Simple and Composite Populations
		PavelKroupa
		CarstenWeidner
		JanPflamm-Altenburg
		IngoThies
		JörgDabringhausen
		MichaelMarks
		ThomasMaschberger
		10.1007/978-94-007-5612-0_4
	Planets, Stars and Stellar Systems
		Springer Netherlands
			2013

[43] Disruption time scales of star clusters in different galaxies
		HJ G L MLamers
		MGieles
		SFPortegies Zwart
		10.1051/0004-6361:20041476
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		429
			1
			
			2005
			EDP Sciences

[44] ALançon
		MMouhcine
	Massive Stellar Clusters
		Astronomical Society of the Pacific Conference Series
		ALançon
		CMBoily
		2000
			211
			34

[45] The mass function of young star clusters in spiral galaxies
		SSLarsen
		10.1051/0004-6361:200811212
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		494
			2
			
			2009
			EDP Sciences

[46] NEW<i>UBVRI</i>PHOTOMETRY OF 234 M33 STAR CLUSTERS
		JunMa
		10.1088/0004-6256/145/4/88
	The Astronomical Journal
		AJ
		0004-6256
		1538-3881
		145
			4
			88
			2012. 2013
			American Astronomical Society
	AJ

[47] Metallicity estimates for old star clusters in M 33
		JunMa
		XuZhou
		JianshengChen
		10.1051/0004-6361:20031556
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		413
			2
			
			2004
			EDP Sciences

[48] Evolution of asymptotic giant branch stars
		PMarigo
		LGirardi
		ABressan
		MA TGroenewegen
		LSilva
		GLGranato
		10.1051/0004-6361:20078467
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		482
			3
			
			2008
			EDP Sciences

[49] Abstracts of papers presented at the joint Meeting of the American Astronomical Society and the Astronomical Society of the Pacific
		PMassey
		KAOlsen
		PWHodge
		10.1086/106179
	The Astronomical Journal
		0004-6256
		54
			33
			2006
			American Astronomical Society

[50] Distances and metallicities for 17 Local Group galaxies
		AWMcconnachie
		MJIrwin
		AM NFerguson
		RAIbata
		GFLewis
		NTanvir
		10.1111/j.1365-2966.2004.08514.x
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		356
			3
			
			2005
			Oxford University Press (OUP)

[51] The Silent Elite: Biologists and the Shaping of Science Policy
		VijayaLMelnick
		DanielMelnick
		10.1007/978-1-4613-2886-5_1
	Biomedical Scientists and Public Policy
		Springer US
			1978
			34

[52] DIRECT Distances to Nearby Galaxies Using Detached Eclipsing Binaries and Cepheids. V. Variables in the Field M31F
		BJMochejska
		JKaluzny
		KZStanek
		MKrockenberger
		DDSasselov
		10.1086/301081
	The Astronomical Journal
		0004-6256
		118
			5
			
			1998
			American Astronomical Society

[53] DNarbutis
		ABridžius
		RStonkutė
	Baltic Astronomy
		16
			421
			2007

[54] A Survey of Star Clusters in the M31 Southwest Field:<i>UBVRI</i>Photometry and Multiband Maps
		DNarbutis
		VVansevičius
		KKodaira
		ABridžius
		RStonkutė
		10.1086/586736
	The Astrophysical Journal Supplement Series
		ASTROPHYS J SUPPL S
		0067-0049
		1538-4365
		177
			1
			
			2008
			American Astronomical Society

[55] FPedregosa
		GVaroquaux
		AGramfort
	Journal of Machine Learning Research
		12
			2825
			2011

[56] A highly abnormal massive star mass function in the Orion Nebula cluster and the dynamical decay of trapezium systems
		JPflamm-Altenburg
		PKroupa
		10.1111/j.1365-2966.2006.11028.x
	Monthly Notices of the Royal Astronomical Society
		Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		373
			1
			
			2006
			Oxford University Press (OUP)

[57] Converting Hα Luminosities into Star Formation Rates
		JanPflamm‐altenburg
		CarstenWeidner
		PavelKroupa
		10.1086/523033
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		671
			2
			
			2007
			American Astronomical Society

[58] MASSCLEAN<i>age</i>—STELLAR CLUSTER AGES FROM INTEGRATED COLORS
		BogdanPopescu
		MMHanson
		10.1088/0004-637x/724/1/296
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		724
			1
			
			2010. 2014
			American Astronomical Society
	ApJ

[59] AGE AND MASS FOR 920 LARGE MAGELLANIC CLOUD CLUSTERS DERIVED FROM 100 MILLION MONTE CARLO SIMULATIONS
		BogdanPopescu
		MMHanson
		BruceGElmegreen
		10.1088/0004-637x/751/2/122
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		751
			2
			122
			2012
			American Astronomical Society

[60] PortegiesZwart
		SFMcmillan
		SL WGieles
		M
	ARA&A
		48
			431
			2010

[61] The near-infrared structure of M33
		MichaelWRegan
		StuartNVogel
		10.1086/174755
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		434
			536
			1994
			American Astronomical Society

[62] The M33 Metallicity Project: Resolving the Abundance Gradient Discrepancies in M33
		ErikRosolowsky
		JoshuaDSimon
		10.1086/527407
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		675
			2
			
			2008
			American Astronomical Society

[63] Evolution of Stars and Stellar Populations
		MaurizioSalaris
		SantiCassisi
		10.1002/0470033452
	Evolution of Stars and Stellar Populations Salpeter E.E. 1955
		Wiley
			2006
			121
			161

[64] SanRoman
		ISarajedini
		AAparicio
		A
	ApJ
		720
			1674
			2010

[65] SanRoman
		ISarajedini
		AGarnett
		DR
	ApJ
		699
			839
			2009

[66] J F CSantosJr
		JAFrogel
	ApJ
		479
			764
			1997

[67] Newly Identified Star Clusters in M33. I. Integrated Photometry and Color-Magnitude Diagrams
		AtaSarajedini
		MKBarker
		DougGeisler
		PaulHarding
		RobertSchommer
		10.1086/509779
	The Astronomical Journal
		AJ
		0004-6256
		1538-3881
		133
			1
			
			2007
			American Astronomical Society

[68] [ITAL]Hubble Space Telescope[/ITAL] WFPC2 Color-Magnitude Diagrams of Halo Globular Clusters in M33: Implications for the Early Formation History of the Local Group
		AtaSarajedini
		DougGeisler
		PaulHarding
		RobertSchommer
		10.1086/311707
	The Astrophysical Journal
		0004-637X
		508
			1
			
			1998
			American Astronomical Society

[69] Hubble Space Telescope WFPC2 Photometry of M33: Properties of the Halo Star Clusters and Surrounding Fields*
		AtaSarajedini
		DougGeisler
		RobertSchommer
		PaulHarding
		10.1086/316807
	The Astronomical Journal
		AJ
		0004-6256
		1538-3881
		120
			5
			
			2000
			American Astronomical Society

[70] A Catalog of Star Cluster Candidates in M33
		AtaSarajedini
		ConorLMancone
		10.1086/518835
	The Astronomical Journal
		AJ
		0004-6256
		1538-3881
		134
			2
			
			2007
			American Astronomical Society

[71] An analytic expression for the luminosity function for galaxies.
		PSchechter
		10.1086/154079
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		203
			297
			1976
			American Astronomical Society

[72] Maps of Dust Infrared Emission for Use in Estimation of Reddening and Cosmic Microwave Background Radiation Foregrounds
		DavidJSchlegel
		DouglasPFinkbeiner
		MarcDavis
		10.1086/305772
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		500
			2
			
			1998
			American Astronomical Society

[73] The star cluster – field star connection in nearby spiral galaxies
		ESilva-Villa
		SSLarsen
		10.1051/0004-6361/201016206
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		529
			A25
			2011
			EDP Sciences

[74] VUrbaneja
		MAKudritzki
		RP
	ApJ
		704
			1120
			2009

[75] COMPACT STAR CLUSTERS IN THE M31 DISK
		VVansevičius
		KKodaira
		DNarbutis
		RStonkutė
		ABridžius
		VDeveikis
		DSemionov
		10.1088/0004-637x/703/2/1872
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		703
			2
			
			2009
			American Astronomical Society

[76] The relation between the most-massive star and its parental star cluster mass
		CWeidner
		PKroupa
		IA DBonnell
		10.1111/j.1365-2966.2009.15633.x
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		401
			1
			
			2010
			Oxford University Press (OUP)

[77] The mmax–Mecl relation, the IMF and IGIMF: probabilistically sampled functions
		CWeidner
		PKroupa
		JPflamm-Altenburg
		10.1093/mnras/stt1002
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		434
			1
			
			2013
			Oxford University Press (OUP)

[78] THE PANCHROMATIC HUBBLE ANDROMEDA TREASURY. IV. A PROBABILISTIC APPROACH TO INFERRING THE HIGH-MASS STELLAR INITIAL MASS FUNCTION AND OTHER POWER-LAW FUNCTIONS
		DanielRWeisz
		MorganFouesneau
		DavidWHogg
		Hans-WalterRix
		AndrewEDolphin
		JulianneJDalcanton
		DanielTForeman-Mackey
		DustinLang
		LClifton Johnson
		LoriCBeerman
		EricFBell
		KarlDGordon
		DimitriosGouliermis
		JasonSKalirai
		EvanDSkillman
		BenjaminFWilliams
		10.1088/0004-637x/762/2/123
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		762
			2
			123
			2013
			American Astronomical Society

[79] Comprehensive stellar population models and the disentanglement of age and metallicity effects
		GuyWorthey
		10.1086/192096
	The Astrophysical Journal Supplement Series
		ApJS
		0067-0049
		1538-4365
		95
			107
			1994
			American Astronomical Society

[80] The chemical abundance in M31 from H <scp>ii</scp>regions
		AZurita
		FBresolin
		10.1111/j.1365-2966.2012.22075.x
	Monthly Notices of the Royal Astronomical Society
		Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		427
			2
			
			2012
			Oxford University Press (OUP)
