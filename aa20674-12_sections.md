# Deriving physical parameters of unresolved star clusters

**Authors:**

- P De Meulenaer <philippe.demeulenaer@ff.stud.vu.lt> (Vilnius University Observatory; Center for Physical Sciences and Technology)
- D Narbutis (Vilnius University Observatory)
- T Mineikis (Vilnius University Observatory; Center for Physical Sciences and Technology)
- V Vansevičius (Vilnius University Observatory; Center for Physical Sciences and Technology)
**Keywords:** galaxies, star clusters, general

**Abstract:**

Context. Stochasticity and physical parameter degeneracy problems complicate the derivation of the parameters (age, mass, and extinction) of unresolved star clusters when using broad-band photometry. Aims. We develop a method to simulate stochasticity and degeneracies and to investigate their influence on the accuracy of derived physical parameters. Then we apply it to star cluster samples of M 31 and M 33 galaxies. Methods. Age, mass, and extinction of observed star clusters are derived by comparing their broad-band U BVRI integrated magnitudes to the magnitudes of a large grid of star cluster models with fixed metallicity Z = 0.008. Masses of stars for a cluster model are randomly sampled from the initial mass function. Models of star clusters from the model grid, which have all of their magnitudes located within 3 observational errors from the magnitudes of the observed cluster, are selected for computing their age, mass, and extinction.Results. In the case of the M 31 galaxy, the extinction range is wide and the age-extinction degeneracy is strong for a fraction of its clusters. Because of a narrower extinction range, the age-extinction degeneracy is weaker for the M 33 clusters. By using artificial cluster sample, we show that age-extinction degeneracy can be reduced significantly if the range of intrinsic extinction within the host galaxy is narrow.

## 1. Introduction

Star clusters are important objects for understanding the formation and evolution of their host galaxies. It is considered that most of star formation is clustered (Lada & Lada 2003), therefore knowledge of the physical parameters of a cluster population (e.g., age, mass, chemical composition, and extinction) is essential for constraining the star formation history of the galaxy.

The commonly used method for deriving the physical parameters of unresolved star clusters is based on comparing of their integrated broad-band photometry colors to the colors of simple stellar population (SSP) models; see, e.g., Anders et al. (2004) and Bridžius et al. (2008). However, this method is strongly biased by the presence of two major problems:

degeneracy between various physical parameters of star clusters; see, e.g., Worthey (1994), Bridžius et al. (2008). For example, a young cluster possessing high extinction can have colors similar to an older object without extinction -an ageextinction degeneracy; stochasticity, which is due to the random presence of a few bright stars, which dominate the integrated photometry of unresolved clusters; see, e.g., Santos & Frogel (1997), Deveikis et al. (2008), Maíz Apellániz (2009). Young clusters can have supergiant stars that significantly redden their integrated colors. By using the SSP method, a much older age would be determined for these clusters.

Figures 6-8 are available in electronic form at http://www.aanda.org Although Cerviño & Luridiana (2006) have attempted to describe the problem of stochasticity analytically, the currently preferred approach (e.g., Popescu & Hanson 2009, 2010;Fouesneau & Lançon 2010;Fouesneau et al. 2012;Asa'D & Hanson 2012) is to use a Monte-Carlo sampling of stellar initial mass function (IMF) to model integrated colors of clusters and build an extensive grid of models, to cover all possible age, mass and extinction ranges. Physical parameters of star clusters are then derived by comparing observations to the grid of models.

Recently Asa 'D & Hanson (2012) have derived the age and extinction of star clusters in the Large Magellanic Cloud (LMC) using the method of Popescu & Hanson (2010) that takes stochasticity into account, and compared results to previous derivations based on an isochrone fit to the resolved colormagnitude diagrams (CMDs). They managed to constrain the age of clusters similar to the values found by the isochrone fit only when previously known extinctions of individual clusters were used.

In this paper, a method of deriving physical parameters is developed and applied to star cluster samples (integrated multiband photometry) in two Local Group galaxies: 1) M 31, using a catalog by Vansevičius et al. (2009), who derived cluster parameters using SSP method; and 2) M 33, using objects common to catalogs of Ma (2012) for photometry and San Roman et al. (2009), who observed in resolved conditions with the Hubble Space Telescope (HST) and estimated age, mass, and extinction based on an isochrone fit to cluster CMDs.

Using this data and artificial cluster simulations, we demonstrate that when the intrinsic range of extinction within the host Article published by EDP Sciences A20, page 1 of 10 galaxy is rather narrow, it is not necessary to know the exact value of the extinction for individual clusters to derive their physical parameters reliably.

The paper is organized into the following sections. Section 2 introduces our method of deriving physical parameters of clusters when stochasticity is taken into account, Sect. 3 describes a grid of simulated cluster models, Sect. 4 presents tests of the method on artificial cluster samples, and Sect. 5 applies the method to the M 31 and M 33 star clusters.

## 2. Method of deriving age, mass, and extinction of star cluster

There are presently two main methods used to derive physical parameters of star clusters based on a 3D grid (age, mass and extinction) of models, which take stochasticity effects into account. The first is a fast χ2 minimization approach used by, e.g., Popescu & Hanson (2010) and Beerman et al. (2012), the second, a more accurate but much slower approach, which builds probability maps in the age-mass-extinction space by exploring all the nodes of the grid and selects the most probable solution (see e.g., Fouesneau & Lançon 2010).

The method presented here also explores parameter probability maps; however, by restricting the analysis to the models located in the vicinity of the observed absolute magnitudes (the distance to the object has to be known), we significantly reduce the computation time. The scheme of the method is sketched in Fig. 1.

A 3D grid of cluster models is built for every value of the three physical parameters t, m, E(B -V) 1 ; for simplicity Fig. 1a shows only a grid for age and mass. For the description of the grid, see Sect. 3. Each node of the grid contains 1000 models of the same age, mass, and extinction. They populate the photometric parameter space (absolute UBVRI magnitudes). Figure 1b shows M U and M B with only 100 models per node without extinction, and the used model grid is much more continuous in photometric parameter space.

When the observations are considered in Fig. 1c, along with their error bars (σ; hereafter we use σ = 0.05 mag for all the passbands of artificial and real cluster samples studied in this paper), which in general can be different for every magnitude, all the models situated within 3-σ from the observed magnitudes are selected. Figure 1d shows the nodes to which the selected models are associated. Other nodes do not play any role in the derivation of parameters, therefore the speed of the algorithm is increased significantly. Finally, the distributions of age and mass, displayed in Figs. 1e,f, are derived from the selected models, as for the extinction, which is not shown in the figure.

For the selected models (Fig. 1c circle) we apply weights as follows: for the models located within 1-σ from the observed magnitude a weight of 0.68 is assigned, for the ones between 1-σ and 2-σ -0.28, and for the ones between 2-σ and 3-σ -0.04. The probability density distributions displayed in Figs. 1e, f are derived by normalizing the total area of each histogram to 1. The solution is taken as the maximum of these 1D distributions. We compute confidence intervals (error bars) by excluding the first and the last 16% of the area in histograms, following the method of "central interval" presented in Sect. 2.5.1 of Andrae (2010). 1 We refer to extinction as E(B -V) hereafter.

## 3. The age-mass-extinction grid of models

To derive physical parameters of star clusters with the method described in Sect. 2, a large age-mass-extinction grid of models is computed, by applying the algorithm described by Deveikis et al. (2008). The stellar masses are generated randomly sampling the IMF (corrected for binaries; Kroupa 2001) and their luminosities are derived from stellar isochrone of the selected age and metallicity of the cluster model. The process is continued until the total mass of generated stars reaches the mass of the cluster model. Then, taking the distance to the cluster into account, the magnitudes are computed using the Johnson-Cousins UBVRI photometric system (Maíz Apellániz 2006).

For stellar models, we took the PADOVA isochrones 2 from Marigo et al. (2008), with corrections by Girardi et al. (2010) for the TP-AGB phases. The model grid for a single metallicity Z = 0.008 contains the following nodes: ages from log (t/yr) = 6.6 to 10.1 in steps of 0.05, masses from log (m/M ) = 2 to 5 in steps of 0.05. This gives 71 values of age and 61 values of mass, and the grid consists of 1000 models per node, i.e. ∼4 × 10 6 stochastic models. To limit the number of models to store in computer's memory, extinction is computed when the observed cluster is compared with the grid of models. It ranges from E(B -V) = 0 to 1 in steps of 0.02, therefore 51 values for the extinction.

To accelerate computation of integrated magnitudes of stochastic star cluster models, we defined a threshold in the isochrone, under which the total luminosity of fainter stars is computed by integration of the stellar luminosity function along the isochrone. Above the threshold, which is defined to select 20% of the most massive stars, the contribution of the highmass stars is modeled by the algorithm of Deveikis et al. (2008). The models built by this improved procedure share the same properties as models built by simulating all stars of the cluster, but require much less computation with a speed gain of a factor ∼10.

## 4. Test of the method on an artificial cluster sample

## 4.1. Degeneracies in an artificial cluster sample

We simulated artificial star cluster samples with known age, mass, and extinction and used them as input clusters to evaluate the ability of our method to derive physical parameters. The artificial cluster samples consist of 10 000 clusters with a random age in the log (t/yr) range of [6.6, 10.1]. To simulate the mass of input clusters, we used a power-law cluster mass function with index -2 in the range of log (m/M ) = [2.7, 4.3], so as to have more low-mass clusters in the sample. We have two artificial samples: one without extinction and the other with E(B -V) in the range of [0.0, 1.0] using the Milky Way standard extinction law from Cardelli et al. (1989). In Fig. 2b, the asymmetry observed in the mass derivation slightly favors high masses. This is because that in the grid of star cluster models, the nodes of models with higher mass have magnitudes that are less dispersed than the nodes with lower mass models, as a consequence of stochasticity (see e.g., Deveikis et al. 2008). Thus, when the models of two nodes of different masses are located in the UBVRI "sphere" around the observation shown in Fig. 1c, the more massive node, with less dispersed models, will dominate. To balance out the effect, a cluster mass function could be used to decrease the importance of the nodes of massive cluster models. Although Fig. 2b shows asymmetry, the means and standard deviations given at log (m/M ) = 3.0, 3.5, and 4.0 indicate that this phenomenon is slight.

Figure 3 gives the results of artificial clusters in the case of extinction. Panels (a), (b), and (c) show the age, mass and extinction derived when there is no photometric errors, and panels (d), (e), and (f) when there are Gaussian photometric errors of 0.05 mag included. In Fig. 3d, in the case of photometric errors and extinction, we observe that a broadening around the one-to-one relation increases, especially for log (t/yr) 8, which is associated with broadening in the extinction (panel f), which is a sign of the age-extinction degeneracy. It creates two streaks above and below the one-to-one relation in the range of 8 < ∼ log (t/yr) < ∼ 9.5 that were already perceptible in the case without photometric errors in Fig. 3a. However, including of photometric errors does not significantly affect the derivation of mass (panels b and e). We note that a gap in derived ages at log (t/yr) = 9.15 is a feature of isochrone due to the increase in the production rate of AGB stars, which was discussed in Girardi & Bertelli (1998). These degeneracy streaks have first been reported by Fouesneau & Lançon (2010). The degeneracy streak above the one-to-one line seen in Fig. 3d concerns clusters that are young and that possess intrinsically high extinction, but are derived by the method as older and having lower extinction. Conversely, the streak of clusters below the one-to-one relation involves objects that are derived as older and that have lower extinction than they do in reality. These features are important to keep in mind when deriving the physical parameters of unresolved star clusters.

The treatment of the metallicity effects on the derivation of age, mass, and extinction of star clusters is the subject of a forthcoming paper. To illustrate the effect, we derived the parameters of a cluster sample of Z = 0.008 metallicity, successively with a model grid of much lower metallicity, Z = 0.00013, and another one with much higher metallicity, Z = 0.03. In the first case, the ages are systematically overestimated by ∼0.5 dex, the upper streak is more developed, and the lower one disappears. The masses are also overestimated by ∼0.5 dex, and there is a preference for overestimated extinction. In the second case, the ages are only slightly (∼0.1 dex) underestimated. The upper streak decreases without vanishing, and the lower one becomes more populated. The masses are underestimated of ∼0.1 dex, and the extinction is almost unaffected.

## 4.2. Is it possible to reduce the age-extinction degeneracy?

The upper and lower streaks in Fig. 3d suggest that if a wide extinction range is allowed in a simulated sample, then there are possibilities that a cluster mimics an older one with lower extinction, or inversely a younger one with higher extinction. If the true extinction range of the cluster population is narrow, then we could restrict the search for the extinction within a narrow range in the model grid, resulting in decrease of age-extinction degeneracy.

In Fig. 4 we show results of the tests for a sample of 10 000 artificial clusters with true extinction from a range of E(B -V) = [0, 0.5] and with Gaussian photometric errors of 0.05 mag randomly added to each magnitude of the sample clusters. This cluster sample was studied twice, with different allowed extinction ranges in the model grid.

In the first test, the extinction of the model grid was allowed to vary in a wide range, E(B -V) = [0, 1], shown in Figs. 4a-c. If a cluster has a true extinction of 0.5, then the maximum underestimation of its extinction can be from 0 to 0.5. But if a cluster has true extinction of 0, the maximum overestimation of its extinction could range from 0 to 1. This explains why the lower streak (i.e. clusters with overestimated extinction) is more extended than the upper one in panel (a).

In the second test, the allowed extinction range of the model grid was reduced to a range of [0, 0.5]; Figs. 4d-f. The constraint on the extinction range resulted in a reduction of the lower degeneracy streak, seen in Fig. 4d, which is less developed than in Fig. 4a. From the comparison of Figs. 4b ande, we see that the mass is less affected by the degeneracy. We note that only the lower streak is modified, since only the higher limit of the allowed extinction range was changed from 1.0 to 0.5. The upper streak is not modified, because the lower limit of the allowed extinction range was not changed.

To quantify the reduction of the lower degeneracy streak due to reduction of the extinction range, all the models situated in the square shown in Figs. 4a andd were counted. There are ∼480 clusters in that region for the wide extinction range (panel a) and only ∼110 for the low extinction range (panel d).

The reduction of the extinction range from E(B -V) = [0, 1] to [0, 0.5] thus decreases more than four times the strength of the degeneracy streak.

We conclude that to reduce the degeneracy streaks seen in Fig. 3d, we should make a reasonable assumption on the extent of the possible extinction range within the galaxy hosting the studied cluster population.

## 5. Application of the method to real star clusters

## 5.1. The M 31 galaxy star cluster sample

A star cluster catalog of 285 objects located in the south west field of the M 31 galaxy was compiled by Narbutis et al. (2008) using the deep BVRI and H α photometry from the Subaru telescope, as well as multiband maps based on HST, Galex, Spitzer, and 2MASS imaging. The UBVRI photometry was derived using the Local Group Galaxy Survey data from Massey et al. (2006). The magnitude limit of the cluster sample was set to the V = 20.5 mag. Vansevičius et al. (2009) selected 238 clusters from that sample, excluding the ones with strong H α emission, and compared their multiband colors to PEGASE (Fioc & Rocca-Volmerange 1997) SSP models to derive their age, mass, metallicity, and extinction. Spitzer data was used to constrain the maximum extinction for each cluster. They reported ∼30 classical globular clusters with low metallicity older than 3 Gyr. The remaining ∼210 younger clusters were classified as objects belonging to the disk, with average metallicity Z = 0.008. Figure 5 shows the U -B vs. B -V and U -V vs. R -I diagrams of the 238 star clusters from Vansevičius et al. (2009), compared to the grid of star cluster models built in Sect. 3. Since our grid of models has single metallicity, Z = 0.008, we attempted to exclude more metal-rich clusters from Vansevičius et al. (2009) sample by only selecting objects with galactocentric distance over 7 kpc. This subsample consists of 216 clusters and is displayed in Fig. 5. It is studied with our method described in Sect. 2, using the Milky Way standard extinction law (Cardelli et al. 1989) and distance modulus to M 31 of (m -M) 0 = 24.47 derived by McConnachie et al. (2005).

Figure 6 presents the age (panels a, b, c), mass (panels d, e, f) and extinction (g, h, i) of 211 clusters (from the 216 sample) derived by using our method; for five clusters, no model was found within the 3-σ around the observed magnitudes. Clusters were studied twice, first with a narrow extinction range E(B -V) = [0.04, 0.5] allowed in the model grid, and second with a wider one, [0.04, 1.0]. The first column (panels a, d, g) compares the age, mass, and extinction derived when a narrow extinction range is allowed vs. the Vansevičius et al. (2009) results. The second column (panels b, e, h) compares the age, mass, and extinction derived when a wide extinction range is allowed vs. the Vansevičius et al. (2009) results. The last column (panels c, f, i) compares the results obtained with a wide extinction range allowed vs. the ones obtained with a narrow extinction range allowed.

In Fig. 6a, when clusters are studied in a narrow allowed extinction range, E(B -V) = [0.04, 0.5], the derived ages show the same features as the models studied in Fig. 3d, reproduced here in the background of the panel. The degeneracy streaks develop above and below the one-to-one line, perpendicularly to it, and are marked by ellipses numbered "1" and "2" in Fig. 6a. As for the models in the background, the upper degeneracy streak concerns clusters with overestimated age and underestimated extinction, shown by ellipse "1" in Fig. 6g. In contrast, for the lower degeneracy streak (ellipse "2"), the age is underestimated and extinction is overestimated. Since the upper streak (ellipse "1") is more developed than the lower one ("2"), we interpret that as a result of too narrow an extinction range in the model grid allowed E(B -V) = [0.04, 0.5].

In Fig. 6b, when clusters are studied in a wider model extinction range, E(B -V) = [0.04, 1], the upper degeneracy streak is less populated, and the lower one extends, meaning that some of the clusters have overestimated extinction (ellipse "3"), also shown in panel (h).

If the intrinsic range of extinction for a cluster sample is wide, as in the galaxy M 31, then a narrow extinction range of models produces extended an upper streak (ellipse "1") and a smaller lower streak (ellipse "2"), shown in Fig. 6a. In panel (b), when the allowed extinction range of models is wide, the upper streak retracts and the lower streak develops. We conclude that in a galaxy with wide extinction range, it is not possible to derive parameters for the clusters affected by age-extinction degeneracy and additional constraints for the extinction are needed; e.g., Vansevičius et al. (2009) used a Spitzer emission map, to trace the dust lanes of M 31 and reduce the age-extinction degeneracy.

Figures 6d,e show that for high-mass clusters we obtain lower masses than given by Vansevičius et al. (2009)  we note that high-mass clusters have metallicities lower than the Z = 0.008 used in our model grid. This could be a sign of the metallicity effect on the derivation of physical parameters, and will be investigated in the forthcoming paper.

## 5.2. The M 33 galaxy star cluster sample

San Roman et al. ( 2009) reports observing of 161 clusters using the HST, allowing them to evaluate their ages and extinctions by PADOVA Girardi et al. (2002) isochrone fit to their resolved CMDs. Recently, Ma (2012) has used 392 clusters from the compiled catalog of Sarajedini & Mancone (2007) and images from Massey et al. (2006) to provide UBVRI broad-band integrated photometry data.

There are 40 clusters common to both the San Roman et al. ( 2009) and the Ma (2012) catalogs, making them interesting to compare the parameters derived from the resolved method (isochrone fit to CMDs by San Roman et al. 2009) and stochastic method, which was applied here to the integrated photometry data of Ma (2012).

Figure 7a presents the U -B vs. B -V diagram of the 392 clusters from the Ma (2012) catalog compared to the grid of cluster models. The selected 40 star clusters are also indicated. To account for calibration of the B band, as discussed by Ma (2012), where he compared his photometry to previous works by Sarajedini & Mancone (2007), Park &Lee (2007), andSan Roman et al. (2009), we shifted the B band to brighter magnitudes by 0.1 mag for all clusters. We note that the parameter derivation results do not change when the B band is not taken into account.

Since the metallicity content of the M 33 galaxy is similar to the one of the LMC (Bresolin et al. 2010), we assume that the interstellar extinction law derived by Gordon et al. (2003) for the LMC can be applied to the M 33 cluster sample. As in We studied the M 33 clusters using two different allowed extinction ranges for the model grid. The first one is narrow, extending between the foreground Galactic line-of-sight extinction in the direction of M 33 up to the higher limit given by U et al. Figure 8 presents the age (panels a, b, c), mass (panels d, e, f), and extinction (g, h, i) of the 40 clusters derived by using our method. The results obtained in the narrow extinction range (panels a, d, g) and the wide extinction range (panels b, e, h) are compared to the ones obtained by San Roman et al. ( 2009) using isochrone fit to CMDs. Panels (c, f, i) compare the results we obtained with the wide extinction range allowed vs. the narrow extinction range allowed. It shows that the difference is relatively small between the two kinds of solution, showing that the agedegeneracy is playing a minor role in this M 33 cluster sample.

The derived mass does not differ significantly, as seen in Fig. 8f. Panels (g, h, i) reveal that only one fourth of the clusters are affected by an increase in extinction when the allowed extinction range is widened. Only some of them have a much higher derived extinction when the wide allowed extinction range is used. These few clusters affected by the age-extinction degeneracy can be seen in panel (c), appearing younger when a wide extinction range is allowed than when the range is narrow, as already seen in M 31 cluster sample in Fig. 6c.

## 6. Conclusions

We presented a method that aims to derive the age, mass, and extinction of unresolved star clusters by using broad-band photometry and taking the stochastic sampling of stellar masses in clusters into account. We investigated the behavior of the method on a sample of artificial star clusters, in order to trace the different degeneracies between parameters, for different choices of photometric errors and extinction.

These tests allowed us to quantify the age-extinction degeneracy. We demonstrated that for the intrinsically narrow extinction range of the star cluster sample, the age-extinction degeneracy can be resolved even in cases where individual exact extinction values are not known for each cluster.

The age-extinction degeneracy has been observed in the real star cluster sample of Vansevičius et al. (2009) for M 31 and to a lesser extent in the one composed of clusters common to the Ma (2012) and San Roman et al. ( 2009) catalogs for M 33. The physical parameters derived by our method for different extinction ranges in each case, have been compared to the values provided in these studies, showing the impact of the age-extinction degeneracy, especially when the true extinction range of the cluster population is wide.

The M 31 star cluster sample from Vansevičius et al. (2009) showed that a true extinction range in this galaxy is wide enough, so that the age-extinction degeneracy is significantly developed, making the parameters difficult to derive, especially for older ages. In such cases, it is preferable to use external constraints on the extinction of individual clusters.

The M 33 star cluster sample shows little sign of ageextinction degeneracy, since there is only a small difference between solutions in narrow and wide extinction ranges. The range of allowed extinction of E(B -V) = [0.04, 0.30] gives parameters consistent with the results of isochrone fit to CMDs San Roman et al. (2009).

The follow-up paper will be dedicated to study of the metallicity effects to derive physical parameters of star clusters and to gain a complete understanding of degeneracies introduced by stochastic effects.

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
		arXiv:1009.2755
		2010

[3] Asa'd
		RSHanson
		MM
	MNRAS
		419
			2116
			2012

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

[5] Planetary nebulae in M33: probes of asymptotic giant branch nucleosynthesis and interstellar medium abundances
		FBresolin
		GStasińska
		JMVílchez
		JDSimon
		ERosolowsky
		10.1111/j.1365-2966.2010.16409.x
	Monthly Notices of the Royal Astronomical Society
		0035-8711
		1365-2966
		404
			1679
			2010
			Oxford University Press (OUP)

[6] ABridžius
		DNarbutis
		RStonkutė
		VDeveikis
		VVansevičius
	Baltic Astron
		17
			337
			2008

[7] The relationship between infrared, optical, and ultraviolet extinction
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

[8] Confidence limits of evolutionary synthesis models
		MCerviño
		VLuridiana
		10.1051/0004-6361:20053283
	Astronomy & Astrophysics
		A&A
		0004-6361
		1432-0746
		451
			2
			
			2006
			EDP Sciences

[9] VDeveikis
		DNarbutis
		RStonkutė
		ABridžius
		VVansevičius
	Baltic Astron
		17
			351
			2008

[10] MFioc
		BRocca-Volmerange
	A&A
		326
			950
			1997

[11] Accounting for stochastic fluctuations when analysing the integrated light of star clusters
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

[12] ANALYZING STAR CLUSTER POPULATIONS WITH STOCHASTIC MODELS: THE<i>HUBBLE SPACE TELESCOPE</i>/WIDE FIELD CAMERA 3 SAMPLE OF CLUSTERS IN M83
		MorganFouesneau
		ArianeLançon
		RupaliChandar
		BradleyCWhitmore
		10.1088/0004-637x/750/1/60
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		750
			1
			60
			2012
			American Astronomical Society

[13] The evolution of the V − K colours of single stellar populations
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

[14] LGirardi
		GBertelli
		ABressan
	A&A
		391
			195
			2002

[15] THE ACS NEARBY GALAXY SURVEY TREASURY. IX. CONSTRAINING ASYMPTOTIC GIANT BRANCH EVOLUTION WITH OLD METAL-POOR GALAXIES
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

[16] A Quantitative Comparison of the Small Magellanic Cloud, Large Magellanic Cloud, and Milky Way Ultraviolet to Near‐Infrared Extinction Curves
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

[17] On the variation of the initial mass function
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

[18] Embedded Clusters in Molecular Clouds
		CharlesJLada
		ElizabethALada
		10.1146/annurev.astro.41.011802.094844
	Annual Review of Astronomy and Astrophysics
		Annu. Rev. Astron. Astrophys.
		0066-4146
		1545-4282
		41
			1
			
			2003
			Annual Reviews

[19] JMa
	AJ
		144
			41
			2012

[20] A Recalibration of Optical Photometry: Tycho-2, Strömgren, and Johnson Systems
		JMaíz Apellániz
		10.1086/499158
	The Astronomical Journal
		AJ
		0004-6256
		1538-3881
		131
			2
			
			2006
			American Astronomical Society

[21] JMaíz Apellániz
	Ap&SS
		324
			95
			2009

[22] Evolution of asymptotic giant branch stars
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

[23] PMassey
		KAOlsen
		PWHodge
	Am. Astron. Soc. Meet. Abstracts
		38
			939
			2006
	BAAS

[24] Distances and metallicities for 17 Local Group galaxies
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

[25] A Survey of Star Clusters in the M31 Southwest Field:<i>UBVRI</i>Photometry and Multiband Maps
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

[26] A Catalog of New M33 Star Clusters Based on<i>Hubble Space Telescope</i>WFPC2 Images
		Won-KeePark
		MyungGyoonLee
		10.1086/522627
	The Astronomical Journal
		AJ
		0004-6256
		1538-3881
		134
			6
			
			2007
			American Astronomical Society

[27] MASSCLEAN—MASSIVE CLUSTER EVOLUTION AND ANALYSIS PACKAGE: DESCRIPTION AND TESTS
		BogdanPopescu
		MMHanson
		10.1088/0004-6256/138/6/1724
	The Astronomical Journal
		The Astronomical Journal
		0004-6256
		1538-3881
		138
			6
			
			2009
			American Astronomical Society

[28] MASSCLEAN<i>age</i>—STELLAR CLUSTER AGES FROM INTEGRATED COLORS
		BogdanPopescu
		MMHanson
		10.1088/0004-637x/724/1/296
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		724
			1
			
			2010
			American Astronomical Society

[29] The M33 Metallicity Project: Resolving the Abundance Gradient Discrepancies in M33
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

[30] NEWLY IDENTIFIED STAR CLUSTERS IN M33. II. RADIAL<i>HUBBLE SPACE TELESCOPE</i>/ADVANCED CAMERA FOR SURVEYS FIELDS
		IzaskunSan Roman
		AtaSarajedini
		DonaldRGarnett
		JonAHoltzman
		10.1088/0004-637x/699/1/839
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		699
			1
			
			2009
			American Astronomical Society

[31] PHOTOMETRIC PROPERTIES OF THE M33 STAR CLUSTER SYSTEM
		IzaskunSan Roman
		AtaSarajedini
		AntonioAparicio
		10.1088/0004-637x/720/2/1674
	The Astrophysical Journal
		ApJ
		0004-637X
		1538-4357
		720
			2
			
			2010
			American Astronomical Society

[32] JrSantos
		JF CFrogel
		JA
	ApJ
		479
			764
			1997

[33] A Catalog of Star Cluster Candidates in M33
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

[34] Maps of Dust Infrared Emission for Use in Estimation of Reddening and Cosmic Microwave Background Radiation Foregrounds
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

[35] U
		VUrbaneja
		MAKudritzki
		R.-P
	ApJ
		704
			1120
			2009

[36] COMPACT STAR CLUSTERS IN THE M31 DISK
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

[37] Comprehensive stellar population models and the disentanglement of age and metallicity effects
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
