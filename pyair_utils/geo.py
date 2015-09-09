#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
** Geoprocessing

Utilitaires de gestion des données spatiales et de calculs géométriques.

Exemple d'utilisation:
jauge = Site('jauge Owen', x=800, y=800, epsg='epsg:2154')
incinerateur = Site('incinerateur', x=100, y=100, epsg='epsg:2154')
jauge.distance_avec(incinerateur)
# 989.94949366009644
jauge.angle_avec(incinerateur)
# 45.000000000000007
jauge.reprojete('epsg:4326')
# (-1.3583799048017915, -5.978598567576917)
jauge.save_in_KML('fichier.kml')
incinerateur.append_to_KML('fichier.kml')
"""

import os
import os.path
import webbrowser
import struct
import pyproj
import simplekml
import shapefile

import numpy as np
import pandas as pd

import utils
from windrose.windrose import histogram


class Site(object):
    """
    Définition d'un site dans le plan

    Paramètres:
    nom: nom du site
    x: longitude du site
    y: latitude du site
    epsg: Système de projection à utiliser en entrée ('epsg:4326' = WGS84)
    """

    def __init__(self, nom, x, y, epsg='epsg:4326'):
        self._set_infos(nom, x, y, epsg)

    def __str__(self):
        return "<Site %s (%s, %s)>" % (self.nom, self.x, self.y)

    def __repr__(self):
        return self.__str__()

    def _set_infos(self, nom, x, y, epsg):
        self.nom = nom
        self.x = x
        self.y = y
        self.epsg = epsg
        self.__geo_interface__ = {'type': 'Point',
                                  'properties': {'name': nom},
                                  'coordinates': (x, y),
                                  }

    def angle_avec(self, origine):
        """
        Renvoie l'angle que forme ce site par rapport à un autre point d'origine
        et le nord (angle site-origine-nord))

        Paramètres:
        origine: Site instance représentant l'origine de l'angle à calculer,
        typiquement l'émetteur (usine)
        """
        xdif = self.x - origine.x
        ydif = self.y - origine.y
        if (xdif == 0) and (ydif == 0):
            print("site %s et origine %s sont identiques" % (self.nom, origine.nom))
            return 9999
        else:
            hypot = np.hypot(xdif, ydif)
            angle = np.degrees(np.arccos(ydif / hypot))
            if xdif < 0:
                return 360 - angle
            else:
                return angle

    def reprojete(self, epsg2='epsg:2154', inplace=False):
        """
        reprojete les coordonnées du site dans un autre système de projection

        Paramètres:
        epsg2: Système de projection à utiliser en sortie ('epsg:2154' = Lambert93)
        inplace: Si oui, l'objet lui-même sera mis à jour avec les nouvelles
        coordonnées et projection, sinon renvoie juste les nouvelles coordonnées
        """
        p1 = pyproj.Proj(init=self.epsg)
        p2 = pyproj.Proj(init=epsg2)
        x, y = pyproj.transform(p1, p2, self.x, self.y)
        if inplace:
            self._set_infos(self.nom, x, y, epsg2)
        else:
            return x, y

    def distance_avec(self, origine, epsg2='epsg:2154'):
        """
        Renvoie la distance du site avec le site d'orgine

        Paramètres:
        origine: Site instance représentant l'origine, typiquement l'émetteur (usine)
        epsg2: système de projection à utiliser pour le calcul des distances
                et le format de sortie ('epsg:2154' = Lambert93)
        """
        xori, yori = origine.reprojete(epsg2)
        xself, yself = self.reprojete(epsg2)
        xdif = xself - xori
        ydif = yself - yori
        if (xdif == 0) and (ydif == 0):
            print("site et origine sont identiques")
            return 0
        else:
            return np.hypot(xdif, ydif)

    def save_in_KML(self, fname='./site.kml'):
        """
        Enregistre le site dans un fichier KML

        Paramètres:
        fname: Nom du fichier à enregistrer
        """
        kml = simplekml.Kml()
        self._append_to_KML(kml)
        kml.save(fname)

    def _append_to_KML(self, kml):
        """
        Ajoute le site à un fichier KML existant

        Paramètres:
        kml: Fichier kml déjà ouvert dans lequel ajouter ce site
        """
        kml.newpoint(name=self.nom, coords=[(self.x, self.y)])

    def show(self):
        """Affiche le point dans Google Maps"""
        x, y = self.reprojete(epsg2='epsg:4326')
        url = "http://maps.google.com/maps?z=12&t=m&q=loc:{}+{}".format(y, x)
        webbrowser.open_new(url)


def angles_avec(sites, origine):
    """
    Calcule l'angle que forme chaque site défini dans la liste sites avec le
    site d'orgine

    Paramètres:
    sites: liste de sites à calculer l'angle (site-origine-nord)
    origine: Site instance représentant l'origine de l'angle à calculer,
        typiquement l'émetteur (usine)

    Retourne :
    un DataFrame contenant les angles calculés

    """

    res = list()
    for s in sites:
        res.append([s.nom, s.angle_avec(origine)])

    df = pd.DataFrame(res, columns=['site', 'angle'])
    df = df.set_index('site')
    return df


def distances_avec(sites, origine, epsg2='epsg:2154'):
    """
    Calcule la distance de chaque site avec le site d'orgine

    Paramètres:
    sites: liste de sites à calculer
    origine: Site instance représentant l'origine, typiquement l'émetteur (usine)
    epsg2: Système de projection à utiliser ('epsg:2154' = Lambert93)

    Retourne :
    un DataFrame contenant les distances calculées

    """

    res = list()
    for s in sites:
        res.append([s.nom, s.distance_avec(origine, epsg2)])

    df = pd.DataFrame(res, columns=['site', 'distance'])
    df = df.set_index('site')
    return df


def sites_from_shapefile(fname, epsg='epsg:4326', col_nom='NOM'):
    """Pour créer des Sites depuis un shapefile

    Paramètres:
    fname: nom du fichier shapefile à traiter
    epsg: Code EPSG (projection) du shapefile
    col_nom: nom de la colonne où trouver les noms des sites à créer

    Retourne:
    Une liste de Site

    """

    sf = shapefile.Reader(fname)
    # shapes = sf.shapes()
    # recs = sf.records()
    idx_nom = np.array(sf.fields)[1:, 0].tolist().index(col_nom)
    print(u"{} enregistrements dans le shapefile".format(sf.numRecords))
    sites = list()
    for r in sf.shapeRecords():
        site = Site(nom=r.record[idx_nom],
                    x=r.shape.points[0][0],
                    y=r.shape.points[0][1],
                    epsg=epsg
                    )
        sites.append(site)
    return sites


def sites_from_df(df, epsg='epsg:4326', nom='nom', x='x', y='y'):
    """ Pour créer des Sites depuis un DataFrame

    Paramètres:
    df: DataFrame à traiter
    epsg: Code EPSG (projection)
    nom: nom de la colonne utilisée pour le paramètre 'nom' de la classe Site
    x: nom de la colonne utilisée pour le paramètre 'x'
    y: nom de la colonne utilisée pour le paramètre 'y'

    """

    sites = [Site(nom=df.loc[i][nom], x=df.loc[i][x], y=df.loc[i][y], epsg=epsg) for i in df.index]
    return sites


def sites_from_csv(fname, epsg='epsg:4326', nom='nom', x='x', y='y', **kwargs):
    """ Pour créer des Sites depuis un fichier CSV

    Paramètres:
    fname: nom du fichier CSV à traiter
    epsg: Code EPSG (projection)
    nom: nom de la colonne utilisée pour le paramètre 'nom' de la classe Site
    x: nom de la colonne utilisée pour le paramètre 'x'
    y: nom de la colonne utilisée pour le paramètre 'y'
    kwargs: paramètres à passer à la fonction read_csv de pandas pour lire le CSV. Se reporter à la doc de pandas
    """
    df = pd.read_csv(fname, **kwargs)
    return sites_from_df(df, epsg=epsg, nom=nom, x=x, y=y)


def save_in_KML(sites, fname='./sites.kml'):
    """
    Enregistre les coordonnées de tous les sites dans un fichier KML ouvrable
    par un SIG ou GoogleEarth

    Paramètres:
    sites: Liste de sites à calculer
    fname: Nom du fichier où enregistrer le kml

    """
    kml = simplekml.Kml()
    for s in sites:
        s._append_to_KML(kml)
    kml.save(fname)
    print('KML enregistré sous %s' % fname)


def vents(vv, dv, origine, sites):
    """
    Calcule les statistiques relatives aux pourcentages d'influence du site émetteur
    d'origine sur les sites récepteurs au travers du calcul de la rose des vents.
    Seuls les vents > 1 m/s seront pris en compte dans les calculs, pour une rose
    des vents de 16 secteurs.

    Paramètres:
    vv: vitesses de vent
    dv: directions du vent
    origine: Site origine des vents à étudier
    sites: liste de sites récepteurs à calculer

    """

    nsector = 16
    classes = np.arange(1, 30, 1)  # classes de vitesses de vent

    vv = vv.astype(float)
    dv = dv.astype(float)
    # suppression des données nulles
    vv, dv = utils.dissolveMask(vv, dv)
    vv = vv.dropna()
    dv = dv.dropna()

    # Calcul des pourcentages de vents par secteur
    dirs, bins, table = histogram(dir=dv, var=vv, bins=classes, nsector=nsector,
                                  normed=False, blowto=True)
    freq = table.sum(axis=0) / table.sum() * 100

    # Création du dataframe des résultats de pourcentages sous les vents
    freq = pd.DataFrame(zip(dirs, freq), columns=('dir_debut', 'pourcentage'))
    # Décalage des directions pour supprimer le problème du secteur nord [350°-10°]
    delta = 360. / nsector / 2
    freq['dir_debut'] = freq['dir_debut'] + delta
    # on ajoute une colonne où sont stockées les directions de fin
    freq['dir_fin'] = freq['dir_debut'].shift(-1)
    freq.at[freq.index[0], 'dir_debut'] = 0.
    freq.at[freq.index[-1], 'dir_fin'] = 360.

    # Calcule des angles et distances des sites par rapport à l'origine
    angles = angles_avec(sites, origine)
    distances = distances_avec(sites, origine)
    # On regroupe angles et distances dans un unique dataframe
    df = angles.join(distances)

    # Pour chaque site, on cherche le pourcentage sous les vents de l'origine
    df['pourcentage'] = 0.
    for idx in df.index:
        ang = df.at[idx, 'angle']
        cond = (ang >= freq['dir_debut']) & (ang < freq['dir_fin'])
        p = freq.get(cond)['pourcentage']
        try:
            df.at[idx, 'pourcentage'] = p
        except:
            pass

    df = df.applymap(np.round)
    return df


def degminsec2DegreDeci(x):
    """Transformes des coordonnées géographiques au format DDMMSS (degré minute
    seconde concatené sur 6 chiffres) au format degrés décimaux
    """
    x = map(str, x)
    x = [i.zfill(12) for i in x]
    ind = np.array([i.find('.') for i in x])
    sec = list()
    min = list()
    deg = list()
    for i in range(len(x)):
        sec.append(x[i].__getslice__(ind[i] - 2, ind[i] + 2))
        min.append(x[i].__getslice__(ind[i] - 4, ind[i] - 2))
        deg.append(x[i].__getslice__(0, ind[i] - 4))
    sec = np.array(sec, dtype=float)
    min = np.array(min, dtype=float)
    deg = np.array(deg, dtype=float)
    return (deg, min, sec)


def degreMinut2DegreDeci(degres=0.0, minutes=0.0, secondes=0.0):
    return degres + (minutes + secondes / 60) / 60


def degreDeci2DegreMinut(degdeci=0.0):
    minutes, degres = np.modf(degdeci)
    minutes = abs(minutes) * 60
    secondes, minutes = np.modf(minutes)
    secondes = secondes * 60
    print ("%i° %i' %.2f'' " % (int(degres), int(minutes), secondes))
    return degres, minutes, secondes


def read_HGT(filename):
    """
    Lit un fichier au format .hgt de la NASA (format raw, 1201*1201 points) et
    renvoie 3 tableaux x, y, z tels que
    x, y: tableau 1D des coordonnées X et Y
    z: tableau 2D des valeurs Z

    Paramètres:
    filename : format [N|S]YY[E|W]XXX.hgt

    """

    # Determination des coordonnées en fonction du nom du fichier
    base, fn = os.path.split(filename)
    fn, ext = os.path.splitext(fn)
    lat = fn[0]
    lon = fn[3]
    y = int(fn[1:3])
    x = int(fn[4:7])
    if lat == 'N':
        y = np.linspace(y, y + 1, 1201)
    else:
        y = np.linspace(y + 1, y, 1201)
    if lon == 'E':
        x = np.linspace(x, x + 1, 1201)
    else:
        x = np.linspace(x + 1, x, 1201)
    y = y[::-1]  # Reverse y

    # Lecture des données
    fp = open(filename, "rb")
    contenu = fp.read()
    fp.close()
    z = np.array(struct.unpack(">1442401H", contenu))  # > = codage big-endian, 1442401 = 1201*1201 valeurs, H=entier
    z = z.reshape((1201, 1201))

    return x, y, z


def save_XYZ(x, y, z, fout=None, get=True, fmt="%.6f"):
    """
    Enregistre un fichier au format .xyz, où chaque ligne est formatée
    au format Xi, Yi, Zi, avec une ligne pour chaque i point de la grille z.
    Si get=True, un tableau de valeurs est retourné et fout n'est pas écrit
    Utile pour enregistrer la sortie de reduceMNT.

    Paramètres:
    x: tableau 1D des coordonnées longitudinales
    y: tableau 1D des coordonnées latitudinales
    z: tableau 2D des valeurs
    fout: nom du fichier de sortie où enregistrer les valeurs
    get: Si vrai, le tableau de valeurs formaté sera renvoyé au lieu d'être inscrit
    dans le fichier de sortie
    fmt: format des données numériques
    """
    xx, yy = np.meshgrid(x, y)
    a = np.transpose(np.array((xx.ravel(), yy.ravel(), z.ravel())))
    if get:
        return a
    else:
        fp = open(fout, 'wb')
        fp.write("x,y,z\n")
        np.savetxt(fp, X=a, delimiter=",", fmt=fmt)
        fp.close()
        # np.savetxt(fname=fout, X=a, delimiter=",", fmt=fmt)


def mass_convert(source="./l2e", s_srs="EPSG:27572", s_form="MapInfo File",
                 target="./l93", t_srs="EPSG:2154", t_form="ESRI Shapefile"):
    """
    Copie tous les fichiers d'un répertoire dans un autre, en appliquant
    une transformation de projection, et une transformation de format.

    Paramètres:
    source: répertoire source
    target: répertoire cible
    s_srs: code epsg du système de projection source
    t_srs: code epsg du système de projection cible
    s_form: format des fichiers sources
    t_form: format des fichiers cibles

    """

    def ext(form):
        if form == "MapInfo File":
            return ".mif"
        if form == "ESRI Shapefile":
            return ".shp"

    CMD = '''ogr2ogr -append -update -f "%s" -s_srs %s -t_srs %s %s %s'''
    for curr_dir, subdirectories, filenames in os.walk(source):
        for filename in filenames:
            fn, ext = os.path.splitext(filename)
            if ext.lower() == ext(s_form):
                s_path = os.path.join(curr_dir, filename)
                print("Traitement de %s" % s_path)
                t_path = os.path.join(target, fn + ext(t_form))
                cmd = CMD % (t_form, s_srs, t_srs, t_path, s_path)
                os.system(cmd)


def rebin_equally(x, y, z, newshape):
    """
    Retourne une sélection de points (X, Y, Z) également espacée dans
    chaque dimension depuis une grille de données de dimensions x*y
    (utile pour la réduction des fichiers terrains pour ADMS)

    Paramètres:
    x: tableau 1D des coordonnées longitudinales
    y: tableau 1D des coordonnées latitudinales
    z: tableau 2D des valeurs
    newshape: nouvelle dimension de la grille 2D résultante
    """
    indy = np.array(np.round(np.linspace(0, z.shape[0] - 1, newshape[0])), dtype=int)
    indx = np.array(np.round(np.linspace(0, z.shape[1] - 1, newshape[1])), dtype=int)
    return x[indx], y[indy], z[indy][:, indx]


def reduct_MNT(fin, xmin, xmax, ymin, ymax, fout=None, get=True):
    """
    Fonction de réduction du domaine d'un fichier MNT au format .ASC (ARC/INFO)

    Paramètres:
    fin : fichier .ASC d'origine
    fout: fichier de sortie
    xmin, xmax, ymin, ymax : zone de réduction
    get : Si True, le nouveau domaine sera retourné tel que (X, Y, VALUES) où
    X les longitudes du nouveau domaine, Y les latitudes, et VALUES les valeurs
    du nouveau domaine. De plus, fout ne sera pas utilisé.

    """
    import matplotlib.pylab as plb

    if fout is None and get == False:
        print("Vous devez fournir un fichier de sortie ou placer le switch 'get' sur 'True' ")
        return
    if not xmin or not xmax or not ymin or not ymax:
        print("Les limites de coordonnées pour le sous domaine doivent être renseignées")
        return

    fp = open(fin, "rb")
    l = fp.readlines()
    l = [i.strip() for i in l]
    fp.close()

    # Récupération des valeurs
    ncols = int(l[0].split()[1])
    nrows = int(l[1].split()[1])
    xllcorner = float(l[2].split()[1])
    yllcorner = float(l[3].split()[1])
    cellsize = float(l[4].split()[1])
    nodata = l[5].split()[1]
    vals = [i.split() for i in l[6:]]
    vals = np.array(vals, dtype=int)
    for i in l[0:6]:
        print(i)

    # Création des vecteurs lats, lons
    X = np.arange(0, ncols, 1) * cellsize + float(xllcorner)
    Y = np.arange(0, nrows, 1) * cellsize + float(yllcorner)
    Y = Y[::-1]  # On inverse car les latitudes sont de bas en haut, alors que les données sont de haut en bas

    # Sélection du sous-domaine
    indx = plb.find((X >= xmin) & (X <= xmax))
    indy = plb.find((Y >= ymin) & (Y <= ymax))
    subdata = vals[indy][:, indx]

    if fout:
        nrows, ncols = subdata.shape
        fp = open(fout, "wb")
        fp.write("ncols %s\r\n" % ncols)
        fp.write("nrows %s\r\n" % nrows)
        fp.write("xllcorner %s\r\n" % X[indx][0])
        fp.write("yllcorner %s\r\n" % Y[indy][-1])
        fp.write("cellsize %s\r\n" % cellsize)
        fp.write("NODATA_value %s\r\n" % nodata)
        np.savetxt(fname=fp, X=subdata, delimiter=" ", fmt="%s")
        fp.close()
    else:
        return X[indx], Y[indy], subdata


def get_center_points(x, y, z=1.5, label="point", delta=5, nb=9, fout=None):
    """
    Génère une grille de points centrée autour d'un point.

    Paramètres:
    x, y: coordonnées du point central
    z: hauteur des points résultants
    label: prefix de l'identiant du point incrémenté suivant label_i
    delta: espacement entre les points, en mètre
    nb: nombre de point par côté de la grille résultante (grille carré).
        Si nb est impair, la grille sera centrée sur le point
    fout: si None, la grille est retranscrite sur la sortie standard, sinon
    un nom de fichier où seront ajoutés les points (nom_projet.asp pour ADMS)

    """

    s = np.arange(-delta * (nb - 1) / 2, delta * (nb + 1) / 2, delta)
    x = x + s
    y = y + s
    x, y = np.meshgrid(x, y)
    x = x.flatten()
    y = y.flatten()
    if fout:
        fp = open(fout, 'ab')
    for i in range(len(x)):
        if fout:
            fp.write("%s_%s,%s,%s,%s\r\n" % (label, i, x[i], y[i], z))
        else:
            print("%s_%s,%s,%s,%s" % (label, i, x[i], y[i], z))
    if fout:
        fp.close()
