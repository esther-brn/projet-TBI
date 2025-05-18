# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 13:30:11 2025

@author: margo
"""

# La fonction check_adress vérifie que le format des adresses entrées est correct
# Les print doivent être remplacés par des messages pop-up sur l'ui

import serial
import sys
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot

"""La fonction check_nb vérifie que le format utilisé est correct (un entier)
Et que la valeur demandée n'est pas trop grande. """
def check_nb(nombre) :
    max = 500 # VALEUR A MODIFIER SI LES SEQUENCES SONT PLUS LONGUES

    try:
        if not (int(nombre) <= max):
            print_error("Valeur incorrecte", "La séquence ne peut pas dépasser 20 actions", QMessageBox.Warning)
            return False
        else:
            return True
    except ValueError:
        print_error("Valeur incorrecte", "La valeur demandée doit être un nombre entier", QMessageBox.Information)
        return False

"""La fonction check_duree vérifie que le format de la durée entrée est correct (un entier)
Et que la valeur demandée est supérieure ou égale au minimum accepté"""
def check_duree(duree, nom) :
    try:
        if nom == 'Intracellulaire':
            if not (int(duree) >= 40):
                print_error("Erreur de durée", "L'intracellulaire doit durer au moins 40 secondes", QMessageBox.Warning)
                return False
            else:
                return True
        else :
            if not (int(duree) >= 12):
                print_error("Erreur de durée", "Le total broth et le surnageant doivent durer au moins 12 secondes", QMessageBox.Warning)
                return False
            else:
                return True
    except ValueError:
        print_error("Erreur de durée", "La durée demandée doit être un nombre entier", QMessageBox.Information)
        return False

"""La fonction check_adress vérifie que le format des adresses entrées est correct
Les print doivent être remplacés par des messages pop-up sur l'ui"""

def check_adress(adr, nb) :
    if adr[:3] == "COM":
        try:
            if not (int(adr[3:]) >= 1 and int(adr[3:]) <= 30):
                print_error(f"Erreur adresse {nb} ", "Ce chiffre ne correspond à aucune COM", QMessageBox.Warning)
                return False
            else :
                return True
        except ValueError:
            print_error(f"Erreur adresse {nb}", "Le format attendu est : COMxx avec xx un entier entre 1 et 20",
                        QMessageBox.Information)
            return False
    else:
        print_error(f"Erreur adresse {nb}", "Le format attendu est : COMxx avec xx un entier entre 1 et 20",
                    QMessageBox.Information)
        return False
        

        
"""La fonction check_flow_rate vérifie que le format du débit entré est correct
Et que la valeur demandée est dans l'intervalle accepté"""
def check_flow_rate(rate) :
    min_rate = 0.2 #valeur minimale de débit acceptée
    max_rate = 0.6 #valeur maximale de débit acceptée

    try :
        if not(float(rate)>=min_rate and float(rate)<=max_rate) :
            print_error("Erreur de débit","Le débit demandé est hors intervalle",QMessageBox.Warning)
    except ValueError :
        print_error("Erreur de débit","Le débit demandé doit être un nombre réel",QMessageBox.Information)
        
    
"""La fonction check_connexion_valco vérifie que la vanne Valco en argument est bien branchée"""
def check_connexion_valco(vanne) : 
    try : 
        data_to_send = "CP\n" #cette commande demande la position actuelle de la vanne
        vanne.write(data_to_send.encode())
    except :
        print_error("Erreur de connexion","La vanne Valco est débranchée",QMessageBox.Critical)

"""La fonction check_connexion_pompe vérifie que la pompe en argument est bien branchée"""
def check_connexion_pompe(pompe) : 
    try : 
        data_to_send = "RF\n"
        pompe.write(data_to_send.encode())
    except :
        print_error("Erreur de connexion","La pompe est débranchée",QMessageBox.Critical)
     
"""La fonction check_connexion_MX vérifie que la vanne MX en argument est bien branchée"""   
def check_connexion_MX(vanne_MX) : 
        try : 
            vanne_MX.get_port()
        except :
            print_error("Erreur de connexion","La vanne MX est débranchée",QMessageBox.Critical)
            
""" La fonction print_error(title,content,level,function) affiche une fenêtre d'erreur 
    avec pour titre title et comme contenu content. 
    Le niveau d'importance (Information, Warning, Critical) est indiqué par le paramètre level
    function désigne la fonction à lancer quand on ferme la fenêtre d'erreur"""
def print_error(title,content,level) :
    msg_box = QMessageBox()
    msg_box.setModal(True)
    msg_box.setIcon(level)
    msg_box.setText(content)
    msg_box.setWindowTitle(title)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.buttonClicked.connect(msg_box.accept)
    msg_box.exec_()
 
#check_nb("wesh")