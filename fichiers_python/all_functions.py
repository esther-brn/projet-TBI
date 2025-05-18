# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 17:04:10 2025

@author: margo
"""

# Ce fichier contient toutes les fonctions (hors gestion d'erreur)

"""
-----------------------------------Partie 0 : Préparation de l'environnement de travail----------------------------
"""

# import de tous les modules nécéssaires
import functions_mxII as mx
import sys
import serial
import logging
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QDialog, QMessageBox
from PyQt5.QtGui import *
from PyQt5 import uic
from threading import Thread
from time import sleep
from error_management import check_adress, check_duree, check_nb, print_error

#initialisation des variables globales
nom_lu=""
duree_lue=0
nb_actions=0
past_actions=0 # variable qui stocke le nb d'actions de la séquence qui ont déjà eu lieu
waiting_thread = Thread(target = sleep, args = (0.1,))

# ces variables vides contiendront les ports séries, on les ouvrira avant de commencer la séquence
vanne_1 = None
vanne_2 = None
vanne_3 = None
vanne_4 = None
pompe_1 = None
pompe_2 = None
#pompe_3 = None
pompe_peri = None
spectro = None

#initialisation du fichier log
logging.basicConfig(            # Configuration du logger
    filename="file_log.log",    # Nom du fichier log
    filemode="w",               # Efface le fichier à chaque exécution
    level=logging.INFO,         # Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Format des logs
    force=True                  # Réinitialise la configuration du logger (et donc permet que la ligne filemode="w" fonctionne)
)

""" 
--------------------------Partie 1 : Définition de la séquence d'actions par l'utilisateur---------------------------   
"""

# chargement des trois interfaces crées indépendamment sous qt designer
Ui_dialog_1, QtBaseClass = uic.loadUiType("choix_nb_actions.ui")
Ui_dialog_2, QtBaseClass = uic.loadUiType("def_actions.ui")
Ui_dialog_3, QtBaseClass = uic.loadUiType("main_window.ui")

# choix_nb_actions ouvre une première fenêtre permettant d'entrer le nb d'actions souhaitées
def choix_nb_actions() :
    
    class dialog_1(QDialog,Ui_dialog_1):
        def __init__(self,parent=None):
            super(dialog_1,self).__init__(parent)
            self.setupUi(self)
            self.move(100, 100)     #affiche l'IU en haut à gauche de l'écran
            
        def valider_nb(self):
            global nb_actions
            if not(check_nb(self.input_nb_actions.text())) :
                return

            nb_actions = self.input_nb_actions.text()
            self.accept()

    app=QApplication(sys.argv)
    form=dialog_1()
    form.show()
    app.exec_()
    return int(nb_actions)

# create_sequence permet de définir une à une les actions de la séquence (nom et durée)
def create_sequence(nb) :

# initialisation du tableau contenant la séquence
    sequence=nb*[None]
    
    class dialog_2(QDialog,Ui_dialog_2):
        
        def __init__(self,parent=None):
            super(dialog_2,self).__init__(parent)
            self.setupUi(self)
            self.move(100, 100)
         
        # valider_action comprend une vérification des durées entrées par l'utilisateur
        # si elles ne sont pas adaptées, un message d'erreur s'affiche
        def valider_action(self):
            global nom_lu,duree_lue
            if not(check_duree(self.text_2.text(), self.text_1.currentText()) ) :
                return
            nom_lu = self.text_1.currentText()
            duree_lue = self.text_2.text()
            self.accept()
    
    
    app=QApplication(sys.argv) 
    form=dialog_2()
    for i in range(nb) :
        
# on donne le numéro de l'action à définir pour ne pas perdre l'utilisateur
        form.label.setText("Informations sur l'action n° "+str(i+1))
        
# on vide la case durée
        form.text_2.setText("")
# on attend avant de rafficher la fenêtre pour ne pas donner l'impression qu'elle clignote
        sleep(0.5)
        form.show()
        app.exec_()
        sequence[i]=[nom_lu,duree_lue]
        
    return sequence


""" 
------------------------------Partie 2 : Création de l'interface principale ---------------------------   
"""
# print_sequence affiche la séquence sous forme de tableau dans l'interface utilisateur principale
# elle restera affichée pendant toute la séquence
# elle affiche également les positions des vannes et les débits des pompes
def print_sequence(tableau) :
    #global window
    class dialog_3(QDialog,Ui_dialog_3):
        def __init__(self,parent=None):
            super(dialog_3,self).__init__(parent)
            self.setupUi(self)
            self.setWindowTitle("Tableau de bord")
            
# appelle la méthode ajout_tableau définie ci-dessous
            self.ajout_tableau()
            
# la méthode initialize est lancée quand l'utilisateur appuie sur le bouton "Démarrer"
            self.start_button.clicked.connect(self.initialize)
            
            self.show()
            
# ajout_tableau ajoute à la fenêtre principale un tableau contenant la séquence entrée par l'utilisateur         
        def ajout_tableau(self):
                
            self.table.setColumnCount(2)
            self.table.setRowCount(len(tableau))
            
            self.table.setHorizontalHeaderLabels(["Nom de l'action","Durée (secondes)"])

            self.table.setColumnWidth(0,200)
            self.table.setColumnWidth(1,220)
            
            for i in range(len(tableau)) :
                self.table.setItem(i,0,QTableWidgetItem(tableau[i][0]))
                self.table.setItem(i, 1, QTableWidgetItem(tableau[i][1]))
                
        """
-----------------------------Partie 3 : initialisation des vannes et des pompes---------------------------------------
        """

# initialize prépare le banc de test (ouverture des ports série, démarrage des pompes...
# puis lance l'exécution de la séquence                
        def initialize(self) :
            
            global pompe_peri, vanne_1, vanne_2, vanne_3, vanne_4, pompe_1, pompe_2, pompe_3, spectro

# lecture des adresses entrées par l'utilisateur et vérification de leur format
            # 1) adresse vanne culture
            adr_1 = self.adr_culture.text()
            if not (check_adress(adr_1,1)) :
                return

            # 2) adresse vanne filtration
            adr_2 = self.adr_filtrage.text()
            if not (check_adress(adr_2, 2)):
                return

            # 3) adresse vanne spectro
            adr_3 = self.adr_spectro.text()
            if not (check_adress(adr_3,3)) :
                return

            # 4) adresse vanne solvant
            adr_4 = self.adr_solvant.text()
            if not (check_adress(adr_4, 4)):
                return

            # 5) adresse pompe 1 (eau stérile)
            adr_5 = self.adr_pompe1.text()
            if not (check_adress(adr_5, 5)):
                return

            # 6) adresse pompe 2 (solvant MS)
            adr_6 = self.adr_pompe2.text()
            if not (check_adress(adr_6, 6)):
                return
            """
            # 7) adresse pompe 3 (solvant d'extraction)
            adr_7 = self.adr_pompe3.text()
            if not (check_adress(adr_7, 7)):
                return
            """

            # 8) adresse pompe péristaltique
            adr_8 = self.adr_peri.text()
            if not (check_adress(adr_8, 8)):
                return

# ouverture des ports série correspondants

            # 1) vanne 1 (Rheodyne côté culture)
            vanne_1 = mx.MX_valve(adr_1, 6, 'vanne culture')
            logging.info(f"Port série {adr_1} (vanne culture) ouvert avec succès.")

            # 2) vanne 2 (Valco pour la filtration)
            vanne_2 = serial.Serial(adr_2, 9600, timeout=1)
            logging.info(f"Port série {adr_2} (vanne filtration) ouvert avec succès.")

            # 3) vanne 3 (Rheodyne côté spectromètre)
            vanne_3 = mx.MX_valve(adr_3, 10, 'vanne spectro')
            logging.info(f"Port série {adr_3} (vanne spectro) ouvert avec succès.")

            # 4) vanne 4 (Rheodyne pour le choix des solvants)
            vanne_4 = mx.MX_valve(adr_4, 6, 'vanne solvant')
            logging.info(f"Port série {adr_4} (vanne solvant) ouvert avec succès.")

            # 5) pompe 1 (eau stérile)
            pompe_1 = serial.Serial(port=adr_5, baudrate=9600, timeout=1)
            logging.info(f"Port série {adr_5} (pompe 1) ouvert avec succès.")

            # 6) pompe 2 (solvant MS)
            pompe_2 = serial.Serial(port=adr_6, baudrate=9600, timeout=1)
            logging.info(f"Port série {adr_6} (pompe 2) ouvert avec succès.")

            """
            # 7) pompe 3 (solvant d'extraction)
            pompe_3 = serial.Serial(port=adr_7, baudrate=9600, timeout=1)
            logging.info(f"Port série {adr_7} (pompe 3) ouvert avec succès.")
            """
            # 8) pompe péristaltique
            pompe_peri = serial.Serial(adr_8, baudrate=9600, timeout=1, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, bytesize=serial.EIGHTBITS)
            logging.info(f"Port série {adr_8} (pompe péristaltique) ouvert avec succès.")
            
            # 9) spectromètre
            spectro = serial.Serial(port= "COM26", baudrate= 9600, timeout= 1) #on suppose qu'il sera toujours connecté au mêm port
            logging.info(f"Port série 'COM26' (spectromètre) ouvert avec succès.")

# placer les deux vannes Rheodyne en position 1-2 (cela correspond au mode injection)
            self.mode_mx('injection')

# placer la vanne Valco dans la position permettant de laisser passer le milieu sans filtrer
            self.mode_valco('passante')

# initialisation de la pompe péristaltique
            # 1) définir la vitesse de rotation en tr/min
            pompe_peri.write(b'1SP30\r')

            # 2) démarrer la pompe
            pompe_peri.write(b'1GO\r')
            logging.info("Démarrage pompe péristaltique")

# initialisation des pompes 1, 2 et 3
            pompe_1.write(b'SF00200\r') #débit à 0.2mL/min pour la pompe 1
            pompe_2.write(b'SF00250\r')
            #pompe_3.write(b'SF00250\r')
            sleep(0.1)
            pompe_1.write(b'RU\r') # démarrage de la pompe 1
            pompe_2.write(b'RU\r')  # démarrage de la pompe 2
            #pompe_3.write(b'RU\r')  # démarrage de la pompe 3
            logging.info('Démarrage des pompes 1 et 2')

# créer et démarrer un timer qui exécute la fonction print_status toutes les 0,5 secondes            
            self.timer=QTimer()
            self.timer.timeout.connect(lambda : self.print_status())
            self.timer.start(1000)
            
            self.exec_sequence(tableau)

        """
------------------------------Partie 4 : Définition des fonctions d'affichage et de commutation-----------------
        """

# print_status met à jour les positions des vannes sur l'interface utilisateur
# à terme, elle doit aussi lire et afficher le débit des pompes et générer un message d'erreur 
# si le débit est trop élevé
        def print_status(self) :
            global vanne_1, vanne_2, vanne_3, vanne_4, pompe_1, pompe_2, pompe_peri

 # Ecrire sur l'interface les positions actuelles des vannes
            # 1) vanne_1 (Rheodyne côté culture)
            pos1 = vanne_1.get_port()
            if pos1 == 1:
                self.pos_culture.setText("1-2")
            elif pos1 == 2:
                self.pos_culture.setText("1-6")
                
            # 2) vanne_2 (Valco pour la filtration)
            vanne_2.write(b'CP\r')
            sleep(0.1)
            if vanne_2.in_waiting > 0:  # Vérifie qu'il y a des bits en attente d'être lus
                pos2 = vanne_2.readline().decode().strip()  # la fonction decode() traduit les bytes en string, puis strip() supprime les caractères spéciaux comme \n
            if pos2 == 'CP01':  # num à changer en fonction du montage réel
                self.pos_filtrage.setText("passante")
            elif pos2 == 'CP02':  # num à changer en fonction du montage réel
                self.pos_filtrage.setText("filtrante")

            # 3) vanne_3 (Rheodyne côté spectro)
            pos3 = vanne_3.get_port()
            if pos3 == 1:
                self.pos_spectro.setText("1-10")
            elif pos3 == 2:
                self.pos_spectro.setText("1-2")
                
            # 4) vanne_4 (Rheodyne côté spectro)
            pos4 = vanne_4.get_port()
            if pos4 == 1:
                self.pos_solvant.setText("A : eau")
            elif pos4 == 2:
                self.pos_solvant.setText("B : extracteur")
                
# Ecrire sur l'interface les débits actuels des pompes
            # 1) pompe_1 (eau stérile)
            # le format de la réponse est : OK00200/ER/
            # on l'écrit sur l'interface au format 0,200 ml/min
            pompe_1.write(b'RF\r')
            sleep(0.1)
            if pompe_1.in_waiting > 0:  # Vérifie qu'il y a des bits en attente d'être lus
                rep_1 = pompe_1.readline().decode().strip()
                debit_1 = rep_1[3:4] + ',' + rep_1[4:7] + " ml/min"
                self.debit_pompe1.setText(debit_1)
                
            # 2) pompe_2 (solvant MS)
            pompe_2.write(b'RF\r')
            sleep(0.1)
            if pompe_2.in_waiting > 0:  # Vérifie qu'il y a des bits en attente d'être lus
                rep_2 = pompe_2.readline().decode().strip()
                debit_2 = rep_2[3:4] + ',' + rep_2[4:7] + " ml/min"
                self.debit_pompe2.setText(debit_2)
            
            """# 3) pompe_3 (solvant extraction)
            pompe_3.write(b'RF\r')
            sleep(0.1)
            if pompe_3.in_waiting > 0:  # Vérifie qu'il y a des bits en attente d'être lus
                rep_3 = pompe_3.readline().decode().strip()
                debit_3 = rep_3[3:4] + ',' + rep_3[4:7] + " ml/min"
                self.debit_pompe3.setText(debit_3)"""
                
            # 4) pompe péristaltique
            # la pompe renvoie son statut au format : 520Du 15.84 520R 9.6MM 220.0 CW P/N 1 123456789 1 !
            # [type depompe] [ml/tour] [tête de pompe] [taille de tube] [vitesse] [HOR/ANTI-HOR] P/N [numéro pompe] [calcul tachymètre] [0/1 (arrêté/en marche)] !                
            pompe_peri.write(b'1RS\r')
            if pompe_peri.in_waiting > 0 :
                rep = pompe_peri.readline().decode().strip()
                debit = rep[23:26] + ',' + rep[27] + ' tr/min'
                self.debit_peri.setText(debit)

# mode_mx fait commuter les vannes 1 et 3 pour passer en injection ou en chargement
        def mode_mx(self,mode) :
            global vanne_1,vanne_3
            if mode == 'chargement' :
                t1 = Thread(target=vanne_1.change_port, args=(2,))  # 2 correspond à la position 1-6
                t1.start()
                t1.join()

                t2 = Thread(target=vanne_3.change_port, args=(1,))  # 1 correspond à la position 1-10
                t2.start()
                t2.join()
                logging.info("Vannes mx en chargement")
            elif mode == 'injection' :
                t1 = Thread(target=vanne_1.change_port, args=(1,))  # 1 correspond à la position 1-2
                t1.start()
                t1.join()

                t2 = Thread(target=vanne_3.change_port, args=(2,))  # 2 correspond à la position 1-2
                t2.start()
                t2.join()
                logging.info("Vannes mx en injection")
                
# mode_solvant fait commuter la vanne 4 pour changer de solvant
        def mode_solvant(self,mode) :
            global vanne_4
            if mode == 'eau' :
                t1 = Thread(target=vanne_4.change_port, args=(1,))  # 1 est la position correspondant à l'eau stérile (solvant A)
                t1.start()
                t1.join()
                logging.info(" Paramétrage du solvant : eau stérile")

            elif mode == 'extract' :
                t2 = Thread(target=vanne_4.change_port,args=(2,))  # 2 est la position correspondant au solvant d'extraction (solvant B)
                t2.start()
                t2.join()
                logging.info(" Paramétrage du solvant : solvant extraction")


# mode_valco fait commuter la vanne valco pour passer en position passante ou filtrante
        def mode_valco(self,mode) :
            global vanne_2
            if mode == 'passante' :
                vanne_2.write(b'GO01\r') # position permettant de laisser passer le milieu sans être filtré (position????)
                sleep(0.1)
                logging.info("Vanne valco passante")
            elif mode == 'filtrante' :
                vanne_2.write(b'GO02\r')  # position permettant de filtrer le milieu (position????)
                sleep(0.1)
                logging.info("Vanne valco filtrante")
 
# start_ms envoie un signal au spectromètre de masse pour lancer son acquisition               
        def start_ms() :
            global spectro
            spectro.setRTS(True)
            
# init_ms remet l'entrée numérique du spectromètre dans son état initial
# la séparation entre start_ms et  init_ms évite d'utiliser la fonction sleep entre les deux commandes
        def init_ms() :
            global spectro
            spectro.setRTS(False)
            
                
        """
-------------------------------------Partie 5 : Définition des modes de prélèvement-----------------------------------------------
        """

        def total_broth(self, tab) :
            global past_actions
            #self.start_ms()
            self.mode_solvant('eau')
            logging.info("Action n° "+ str(past_actions+1)+" : total broth en cours")
            self.mode_valco('passante') # initialise la vanne de filtrage en mode passant
            QTimer.singleShot(5900,lambda:self.mode_mx('chargement')) # après 6 secondes, passage en mode chargement
            QTimer.singleShot(11900,lambda:self.mode_mx('injection')) # après 12 secondes, retour en mode injection
            QTimer.singleShot(int(tableau[past_actions][1])*1000-100,lambda:logging.info("Fin total broth"))
            #self.init_ms()
            past_actions +=1
    
        def compart_extracellulaire(self,tab) :
            global past_actions
            #self.start_ms()
            self.mode_solvant('eau')
            logging.info("Action n° "+ str(past_actions+1)+" : extracellulaire en cours")
            self.mode_valco('filtrante')
            QTimer.singleShot(5900,lambda: self.mode_mx('chargement')) # après 6 secondes, passage en mode chargement
            QTimer.singleShot(11900,lambda: self.mode_mx('injection')) # après 12 secondes, retour en mode injection
            QTimer.singleShot(int(tableau[past_actions][1])*1000-100,lambda:logging.info("Fin extracellulaire"))
            #self.init_ms()
            past_actions += 1
            
        def compart_intracellulaire(self, tab) :
            global past_actions
            #self.start_ms()
            self.mode_solvant('eau')
            logging.info("Action n° "+ str(past_actions+1) +" : intracellulaire en cours")
            self.mode_valco('filtrante')
            # 1) On fait passer le surnageant à travers le filtre
            QTimer.singleShot(5900, lambda: self.mode_mx('chargement'))  # après 6 secondes, passage en mode chargement
            QTimer.singleShot(11900, lambda: self.mode_mx('injection'))  # après 12 secondes, retour en mode injection

            # 2) On change de solvant
            QTimer.singleShot(12000, lambda: self.mode_solvant('extract'))

            # 3) On remplit  passer le solvant B à travers le filtre
            QTimer.singleShot(29900, lambda: self.mode_mx('chargement'))  # après 6 secondes, passage en mode chargement
            QTimer.singleShot(35900, lambda: self.mode_mx('injection'))  # après 12 secondes, retour en mode injection
            QTimer.singleShot(int(tableau[past_actions][1])*1000-100,lambda:logging.info("Fin intracellulaire"))
            #self.init_ms()
            past_actions += 1
    
        """
-----------------------------Partie 6 : Définition des fonctions pour exécuter la séquence---------------------------------
        """
 
# exec_sequence parcourt le tableau contenant la séquence et appelle les modes de prélèvement correspondants           
        def exec_sequence(self, tableau) :
            logging.info("Démarrage du programme")
            delay = 0
            for i in range(len(tableau)) :
                if tableau[i][0] == "Total broth" :
                        QTimer.singleShot(delay*1000, lambda :self.total_broth(tableau))
                elif tableau[i][0] == "Surnageant" :
                        QTimer.singleShot(delay*1000, lambda :self.compart_extracellulaire(tableau))
                elif tableau[i][0] == "Intracellulaire" :
                        QTimer.singleShot(delay*1000, lambda :self.compart_intracellulaire(tableau))
                delay += int(tableau[i][1])
            QTimer.singleShot((delay+2)*1000, lambda : self.fin_programme())
 
# fin_programme arrête toutes les pompes, ferme les ports série et ferme la fenêtre principale            
        def fin_programme(self)  :
            global pompe_peri, vanne_1, vanne_2, vanne_3, vanne_4, pompe_1, pompe_2, pompe_3, spectro
            
            # arrêter les pompes et fermer les ports série associés
            pompe_peri.write(b'1ST\r')
            pompe_peri.close()

            pompe_1.write(b'ST\r')
            pompe_1.close()

            pompe_2.write(b'ST\r')
            pompe_2.close()
            
            """
            pompe_3.write(b'ST\r')
            pompe_3.close()
            """
            
            # fermer les autres ports série
            vanne_1.close()
            vanne_2.close()
            vanne_3.close()
            #vanne_4.close()
            #spectro.close()

            logging.info("Fin du programme")
            print("Les logs ont été enregistrés dans 'file_log.log'.")
            self.accept()
    
    App = QApplication(sys.argv)
    window = dialog_3()
    sys.exit(App.exec())
    return window