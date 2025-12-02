import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from reportlab.lib.utils import ImageReader
from streamlit_js_eval import streamlit_js_eval
import json
import io
import os
import ezdxf
from ezdxf import path
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Rectangle, Circle


# Charger les traduction depuis un fichier excel 
@st.cache_data  
def charger_traductions():
    df = pd.read_excel("traductions.xlsx")
    trads = {}
    for _, row in df.iterrows():
        key = row["key"]
        trads[key] = {
            "Français": row.get("FR", key),
            "English": row.get("EN", key),
            "Italiano": row.get("IT", key),
            "Deutsch": row.get("DE", key)
        }
    return trads

# Fonction de traduction
def t(key):
    langue = st.session_state.get("langue", "Français")
    return trads.get(key, {}).get(langue, key)

# choix de langue # SOUS PROGRAMME #
def choix_langue():
    if "langue" not in st.session_state:
        st.session_state.langue = "Français"

    langue = st.session_state.get("langue", "Français")
    st.selectbox("🌐 Langue / Language", ["Français", "English", "Italiano", "Deutsch"], key="langue")  

# Charger et lire base de donée excel avec les réferences # SOUS PROGRAMME #
@st.cache_data
def charger_base():
    return pd.read_excel("base_references.xlsx")

def initialisation_infos_client():
    if "hau_arm" not in st.session_state:
       st.session_state["hau_arm"] = 2000
    if "lar_arm" not in st.session_state:
       st.session_state["lar_arm"] = 600
    if "marq_arm" not in st.session_state:
       st.session_state["marq_arm"] = ""
    if "ref_arm" not in st.session_state:
       st.session_state["ref_arm"] = ""
    if "ref_projet" not in st.session_state:
       st.session_state["ref_projet"] = ""
    if "commentaire_projet" not in st.session_state:
       st.session_state["commentaire_projet"] = ""
    if "etrier" not in st.session_state:
        st.session_state["etrier"] = "EM80"
    if "montant" not in st.session_state:
        st.session_state["montant"] = "MSF12"   
    if "couleur_pc" not in st.session_state:
        st.session_state["couleur_pc"] = "Bleu"

# Configuration des infos clients sur la sidebar # SOUS PROGRAMME #
def infos_clients():
    st.sidebar.image("logo.jpg")
    with st.sidebar.expander(t("info_arm_txt"), expanded=False):

        st.write(t("hauteur_arm_txt"))
        hauteur_armoire = st.number_input(
            "",
            min_value=100, max_value=3000, step=100,
            key="hau_arm"
        )

        st.write(t("largeur_arm_txt"))
        largeur_armoire = st.number_input(
            "",
            min_value=100, max_value=2000, step=100,
            key="lar_arm"
        )

        st.write(t("marque_arm_txt"))
        marque_armoire = st.text_input(
            "",
            key="marq_arm"
        )

        st.write(t("reference_arm_txt"))
        reference_armoire = st.text_input(
            "",
            key="ref_arm"
        )

    with st.sidebar.expander(t("info_projet_txt"), expanded=False):

        st.write(t("reference_projet_txt"))
        reference_projet = st.text_input(
            "",
            key="ref_projet"
        )

        st.write(t("commentaire_projet_txt"))
        commentaire_projet = st.text_area(
            "",
            key="commentaire_projet"
        )

    return hauteur_armoire, largeur_armoire
    
# Section d'ajout des différents profils # SOUS PROGRAMME #
def selection_empillage():
    st.subheader(t("ajouter_empilage_txt"))
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])

    type_element = col1.selectbox(t("type_profil_txt"), df_refs["Type"].unique(), key="type_sel")
    ref_options = df_refs[df_refs["Type"] == type_element]["Référence"].dropna().tolist()

    if type_element == "Empty":
       reference = col2.selectbox(t("ref_profil_txt"), ref_options, key="ref_sel_vide")
       hauteur = col3.number_input(t("hauteur_vide_txt"), 1, 1000, step=5, format="%d", key="haut_vide")
    else:
        reference = col2.selectbox(t("ref_profil_txt"), ref_options, key="ref_sel")
        matching = df_refs[(df_refs["Type"] == type_element) & (df_refs["Référence"] == reference)]
        if not matching.empty and "Hauteur (mm)" in matching.columns:
          hauteur = int(matching["Hauteur (mm)"].values[0])
          col3.markdown(f"**{t("hauteur_auto_txt")} :** {hauteur} mm")
        
    if col4.button(t("ajouter_txt")):
      st.session_state.empilage.append({
       "Type": type_element,
       "Référence": reference,
       "Hauteur (mm)": int(hauteur),
       # on initialise tout de suite les peignes si applicable
        "peigne_haut": True if type_element in ["PP (flat)", "PPA (DIN rail)"] else False,
        "peigne_bas": True if type_element in ["PP (flat)", "PPA (DIN rail)"] else False
      })
      st.rerun() 

# Ajout du tableau d'empillage # SOUS PROGRAMME #
def tableau_empillage(h):
 HAUTEUR_PEIGNE = 15
 df_emp = pd.DataFrame(st.session_state.empilage)
 if not df_emp.empty:
    df_emp["Hauteur (mm)"] = df_emp["Hauteur (mm)"].astype(int)
   
    total = 0

    # Calcul total avec peignes #
    for i, row in enumerate(df_emp.itertuples(index=False, name=None)):
        hauteur_module = int(row[2])
        mod = st.session_state.empilage[i]

        # ajout hauteur peigne si coché #

        if mod.get("peigne_haut", False):
            hauteur_module += HAUTEUR_PEIGNE
        if mod.get("peigne_bas", False):
            hauteur_module += HAUTEUR_PEIGNE
        total += hauteur_module

    hauteur_montant = h - 100
    hauteur_disponible = hauteur_montant - total

    st.markdown(f"### {t('tableau_empilage_txt')}")
    empilage_modifié = st.session_state.empilage.copy()
    changement = False
    st.info(f"{t("hauteur_montant_txt")} : {hauteur_montant} mm")
    st.warning(f"{t("hauteur_dispo_txt")} : {hauteur_disponible} mm") 
 headers = st.columns([1, 2, 2, 2, 1, 1, 2])
 headers[0].markdown(f"**{t('actions_txt')}**")
 headers[1].markdown(f"**{t('type_profil_txt')}**")
 headers[2].markdown(f"**{t('ref_profil_txt')}**")
 headers[3].markdown(f"**{t('hauteur_txt')}**")
 headers[4].markdown(f"**{t('peigne_haut')}**")
 headers[5].markdown(f"**{t('peigne_bas')}**")
 headers[6].markdown(f"**{t('options_txt')}**")

 # Ajout des boutons d'interactions #
 action = None
 index_action = None

 for i, row in enumerate(df_emp.itertuples(index=False, name=None)):
    col_btns, col_type, col_ref, col_haut, col_haut_peigne, col_bas_peigne, col_val = st.columns([1, 2, 2, 2, 1, 1, 2])
    with col_btns:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬆️", key=f"up_{i}") and i > 0:
                action = "up"
                index_action = i
        with col2:
            if st.button("⬇️", key=f"down_{i}") and i < len(empilage_modifié)-1:
                action = "down"
                index_action = i
        with col3:
            if st.button("🗑️", key=f"del_{i}"):
                action = "delete"
                index_action = i

    col_type.write(row[0])
    col_ref.write(row[1])
    col_haut.write(f"{row[2]} mm")

    # Initialiser si absent
    if "peigne_haut" not in st.session_state.empilage[i]:
        st.session_state.empilage[i]["peigne_haut"] = True if row[0] in ["PP (flat)", "PPA (DIN rail)"] else False
    if "peigne_bas" not in st.session_state.empilage[i]:
        st.session_state.empilage[i]["peigne_bas"] = True if row[0] in ["PP (flat)", "PPA (DIN rail)"] else False

    # Affichage checkbox si applicable
    if row[0] in ["PP (flat)", "PPA (DIN rail)"]:
      old_haut = st.session_state.empilage[i]["peigne_haut"]
      old_bas = st.session_state.empilage[i]["peigne_bas"]

      new_haut = col_haut_peigne.checkbox(
          "",
          value=old_haut,
          key=f"haut_{i}"
      )
      new_bas = col_bas_peigne.checkbox(
          "",
          value=old_bas,
          key=f"bas_{i}"
      )

      # Met à jour l’état
      st.session_state.empilage[i]["peigne_haut"] = new_haut
      st.session_state.empilage[i]["peigne_bas"] = new_bas

      # Si une case a changé → recalcul immédiat
      if new_haut != old_haut or new_bas != old_bas:
          st.rerun()
          col_haut_peigne.write("-")
          col_bas_peigne.write("-")


    with col_val:
         if st.button(t("option_bouton_txt"), key=f"option_{i}"):
            st.session_state.selected_profil_index = i
                
 # Exécuter l'action sélectionnée après la boucle
 if action == "up" and index_action > 0:
    empilage_modifié[index_action - 1], empilage_modifié[index_action] = empilage_modifié[index_action], empilage_modifié[index_action - 1]
    st.session_state.empilage = empilage_modifié
    st.rerun()
 elif action == "down" and index_action < len(empilage_modifié) - 1:
    empilage_modifié[index_action + 1], empilage_modifié[index_action] = empilage_modifié[index_action], empilage_modifié[index_action + 1]
    st.session_state.empilage = empilage_modifié
    st.rerun()
 elif action == "delete":
    empilage_modifié.pop(index_action)
    st.session_state.empilage = empilage_modifié
    st.rerun()

# Ajout des options selons profils dans la sidebar # SOUS PROGRAMME #
def options_profils():
    index = st.session_state.get("selected_profil_index", None)
    if index is None:
        return

    # Vérifie que l'index est encore valide après suppression
    if index < 0 or index >= len(st.session_state.empilage):
        st.session_state.selected_profil_index = None
        return
    profil = st.session_state.empilage[index]

    st.sidebar.markdown(f"### {t('option_profil_txt')}")
    st.sidebar.write(f"{t("type_profil_txt")} : {profil['Type']}")
    st.sidebar.write(f"{t("ref_profil_txt")} : {profil['Référence']}")
 
    # Initialiser structure si absente
    if "options" not in profil:
        profil["options"] = {}

    # OPTIONS SPÉCIFIQUES : PROFIL PLAT → Rail DIN
    if profil["Type"] == "PP (flat)":
        rail_opts = profil["options"].get("rail_din", {})
        longueur = rail_opts.get("longueur", 50)
        position = rail_opts.get("position", 0)

        with st.sidebar.expander(t("ajout_din"),expanded=False):      
             longueur_input = st.number_input(t("longueur_txt"), 50, 2000, longueur, step=10, key=f"longueur_{index}")
             position_input = st.number_input(t("position_gauche"), 0, 2000, position, step=10, key=f"position_{index}")

             col1, col2 = st.columns(2)
             with col1:
                 if st.button("✅", key=f"valider_option_{index}"):
                    profil["options"]["rail_din"] = {
                             "enabled": True,
                             "longueur": longueur_input,
                             "position": position_input
                         }
                    st.success(t("din_enregistre"))

        with col2:
            if st.button("🗑️", key=f"supprimer_option_{index}"):
                if "rail_din" in profil["options"]:
                    del profil["options"]["rail_din"]
                    st.success(t("din_supprime"))
        
    
    # OPTIONS PM VERTICALE (PM38)
    if profil["Type"] in ["PP (flat)", "PPA (DIN rail)"]:

        pm_old = profil["options"].get("pm_verticale", {})

        longueur_pm = pm_old.get("longueur", 100)
        position_pm = pm_old.get("position", 0)
        entraxe_pm = pm_old.get("entraxe", 0)

        # Écrous PM38 existants
        ec_pm_old = pm_old.get("ecrous_pm38", {"type": "M4", "quantite": 2})

        with st.sidebar.expander(t("ajout_pm"), expanded=False):

            # --- Paramètres PM38 ---
            longueur_input = st.number_input(
                t("longueur_txt"), 20, 2000, longueur_pm,
                step=10, key=f"pm_len_{index}"
            )

            position_input = st.number_input(
                t("position_gauche"), 0, 2000, position_pm,
                step=10, key=f"pm_pos_{index}"
            )

            entraxe_input = st.number_input(
                t("entraxe_txt"), 0, 2000, entraxe_pm,
                step=10, key=f"pm_entr_{index}"
            )

            col1, col2 = st.columns(2)

            # --- BOUTON SAUVEGARDE PM38 (icône OK) ---
            with col1:
                if st.button("✅ Enregistrer PM38", key=f"pm_save_{index}"):

                    profil["options"]["pm_verticale"] = {
                        "enabled": True,
                        "longueur": longueur_input,
                        "position": position_input,
                        "entraxe": entraxe_input,
                        "ecrous_pm38": ec_pm_old   # <-- CRUCIAL : on garde les écrous
                    }

                    st.success("PM38 enregistré !")

            # --- BOUTON SUPPRIMER PM38 (icône poubelle) ---
            with col2:
                if st.button("🗑️ Supprimer PM38", key=f"pm_delete_{index}"):
                    if "pm_verticale" in profil["options"]:
                        del profil["options"]["pm_verticale"]
                    st.success("PM38 supprimé")

            # --- Options ÉCROUS PM38 ---
            st.markdown("### 🔩 Écrous PM38")

            type_ec = st.selectbox(
                "Type d'écrou",
                ["M4", "M5", "M6", "M8"],
                index=["M4", "M5", "M6", "M8"].index(ec_pm_old.get("type", "M4")),
                key=f"pm38_type_{index}"
            )

            qty_ec = st.number_input(
                "Quantité d'écrous", 1, 20,
                ec_pm_old.get("quantite", 2),
                step=1, key=f"pm38_qty_{index}"
            )

            if st.button("💾 Enregistrer écrous PM38", key=f"pm38_save_{index}"):

                profil["options"].setdefault("pm_verticale", {})["ecrous_pm38"] = {
                    "type": type_ec,
                    "quantite": qty_ec
                }

                st.success("Écrous PM38 enregistrés")

    

    # OPTION ECROUS DANS PROFILS #

    if profil["Type"] in ["PP (flat)", "PPA (DIN rail)", "Accesoires"]:
       with st.sidebar.expander(t("ajout_ecrou"),expanded=False):
            ecrous_opts = profil["options"].get("ecrous", {})

            type_ecrou = ecrous_opts.get("type", "M4")
            quantite = ecrous_opts.get("quantite", 1) 

            type_input = st.selectbox(t("type_ecrou_txt"), ["M4", "M5", "M6", "M8"], index=["M4", "M5", "M6", "M8"].index(type_ecrou), key=f"ecrou_type_{index}")
            quantite_input = st.number_input(t("quantite_txt"), 1, 100, quantite, step=1, key=f"ecrou_qte_{index}")

            col1, col2 = st.columns(2)
            with col1:
                 if st.button("✅", key=f"valider_ecrou_{index}"):
                    profil["options"]["ecrous"] = {
                     "type": type_input,
                     "quantite": quantite_input,
                     "enabled": True
                    }
                    st.success(t("ecrou_enregistre"))
            with col2:
                 if st.button("🗑️", key=f"supprimer_ecrou_{index}"):
                    if "ecrous" in profil["options"]:
                        del profil["options"]["ecrous"]
                        st.success(t("ecrou_supprime"))

    # COMMENTAIRES CLIENTS #

    st.sidebar.markdown(t("commentaire_txt"))
    commentaire = profil.get("commentaire", "")

    nouveau_commentaire = st.sidebar.text_area(t("ajout_commentaire"), commentaire, key=f"commentaire_{index}")

    # Sauvegarde si modifié
    if nouveau_commentaire != commentaire:
        profil["commentaire"] = nouveau_commentaire
   
# Affichage d'un visuel châssis # SOUS PROGRAMME #
def visuel_chassis(h, la, show=True):
    

    fig_width_inch = 6
    fig_height_inch = 10
    fig, ax = plt.subplots(figsize=(fig_width_inch, fig_height_inch)) 

    #définir l'échelle mm en pouces
    largeur_profil = la -100 #largeur réel du châssis
    mm_to_inch = 1 / 24.4 

    ax.set_xlim(0, la)
    ax.set_ylim(0, la)
    ax.invert_yaxis()  # Pour que le haut du châssis soit en haut du dessin

    current_y = 0 #point de départ du haut
    # Couleur dynamique peignes/capots
    if st.session_state.get("couleur_pc", "Bleu") == "Gris":
        couleur_peigne = "#c5c5c5"    # gris clair
        couleur_capot  = "#b6b6b6"    # gris moyen
    else:
        couleur_peigne = "#2327F3"    # bleu clair
        couleur_capot  = "#1A07C5"    # bleu foncé
    couleur_profil = "#979591FF"
    # Tableau des couleurs

    couleurs_type = {
        "PPA (DIN rail)": couleur_profil,
        "peigne": couleur_peigne,      # dynamique
        "CPF": couleur_capot,          # dynamique
        "Empty": "#fcfcfc",
        "PP (flat)": couleur_profil,
        "Accesoires": couleur_profil
    }
    
       
    # CREATION AXE VISUEL #
    fig, ax = plt.subplots(figsize=(fig_width_inch, fig_height_inch))

    # Zone de tracé en mm
    ax.set_xlim(-50, la + 50)  # Laisse un peu de marge à gauche pour la graduation
    ax.set_ylim(0, h)
    ax.invert_yaxis()

    # Affichage de l’échelle verticale tous les 100 mm
    graduation_interval = 100
    for y in range(0, h , graduation_interval):
     ax.hlines(y, -5, -30, color='black', linewidth=0.3)
     ax.text(-50, y, f"{y} mm", va='center', ha='right', fontsize=5)

    # FIN CREATION AXE VISUEL #



     # --- MONTANTS VERTICAUX GAUCHE ET DROITE ---
    largeur_montant = 30  # en mm
    hauteur_montant = h - 100  # comme dans le calcul global

     # Montant gauche
    ax.add_patch(patches.Rectangle(
    (0, 0),
    largeur_montant,
    hauteur_montant,
    facecolor="#888888", edgecolor="black", linewidth=0.5,
    zorder=1
    ))

    # Montant droit
    ax.add_patch(patches.Rectangle(
    ((la - 70 - largeur_montant) - largeur_montant, 0),
    largeur_montant,
    hauteur_montant,
    facecolor="#888888", edgecolor="black", linewidth=0.5,
    zorder=1
    ))

    
    for elt in st.session_state.empilage:
        hauteur = elt["Hauteur (mm)"]
        type_elt = elt["Type"]
        color = couleurs_type.get(type_elt, "#CCCCCC")

        peigne_haut = elt.get("peigne_haut", True)
        peigne_bas = elt.get("peigne_bas", True)
        peigne_height = 15  # mm visuel utilisé pour ajuster les positions

        # Si peigne haut : décaler vers le bas
        if peigne_haut:
           current_y += peigne_height


        # Profil
        zorder=0 if type_elt == "Empty" else 2
        linewidth=0 if type_elt =="Empty" else 0.3
        rect = patches.Rectangle((0, current_y), largeur_profil, hauteur, facecolor=color, edgecolor='black', linewidth=linewidth, zorder=zorder)
        ax.add_patch(rect)
        ax.text(la + 10, current_y + hauteur / 2, elt["Référence"], va='center', fontsize=6)
        

        # AFFICHAGE DES RAINURE PROFILS #
          
        if type_elt in ["PP (flat)", "PPA (DIN rail)", "Accesoires"]:
           # Aller chercher les rainures depuis la base Excel
           reference = elt["Référence"]
           rainure_info = df_refs[df_refs["Référence"] == reference]
    
           if not rainure_info.empty and "Rainures Y (mm)" in rainure_info.columns:
               val = rainure_info.iloc[0]["Rainures Y (mm)"]
               if pd.notna(val):
                   try:
                       positions = [float(y.strip()) for y in str(val).split(";") if y.strip()]
                       for y_rel in positions:
                           y_line = current_y + y_rel
                           ax.hlines(
                               y=y_line,
                               xmin=0,  # ou 50 si tu veux à l'intérieur du châssis
                               xmax=largeur_profil,
                               color='black',
                               linewidth=0.2,
                              
                            )
                   except:
                         pass

        # --- PEIGNES ---
        if type_elt in ["PP (flat)", "PPA (DIN rail)"]:
            largeur_peigne = largeur_profil
            hauteur_peigne = 15  # visuel
            x_peigne = 0

            if peigne_haut:
                y_haut = current_y
                ax.add_patch(patches.Rectangle(
                    (x_peigne, y_haut - hauteur_peigne),
                    largeur_peigne,
                    hauteur_peigne,
                    facecolor=couleurs_type.get("peigne"),
                    edgecolor='black',
                    linewidth=0.2
                ))
                ax.text(
                    la + 10,
                    y_haut - hauteur_peigne / 2,
                    "PF300",
                    ha="left",
                    va="center",
                    fontsize=5
                )

            if peigne_bas:
                y_bas = current_y + hauteur
                ax.add_patch(patches.Rectangle(
                    (x_peigne, y_bas),
                    largeur_peigne,
                    hauteur_peigne,
                    facecolor=couleurs_type.get("peigne"),
                    edgecolor='black',
                    linewidth=0.2
                ))
                ax.text(
                    la + 10,
                    y_bas + hauteur_peigne / 2,
                    "PF300",
                    ha="left",
                    va="center",
                    fontsize=5
                )

        # AFFICHAGE PM38
        pm = elt.get("options", {}).get("pm_verticale", None)
        if pm and pm.get("enabled"):

            largeur_pm = 38  # mm
            hauteur_pm = pm.get("longueur", 100)
            position_x = pm.get("position", 0)
            entraxe = pm.get("entraxe", 0)

            y_top = current_y  # point haut du profil actuel

            # Lignes PM38 (bords + internes)
            lignes_pm = [0, 7.75, 16.25, 24, 38]

            # On récupère les écrous PM38
            pm38_ec = pm.get("ecrous_pm38", None)

            for offset in [0, entraxe] if entraxe > 0 else [0]:

                # ==== BORD GAUCHE RÉEL DU PM38 ====
                x_left = position_x + offset

                # ----- Rectangle du PM38 -----
                ax.add_patch(patches.Rectangle(
                    (x_left, y_top),
                    largeur_pm,
                    hauteur_pm,
                    facecolor="grey",
                    edgecolor="black",
                    linewidth=0.3,
                    zorder=15
                ))

                # ----- Lignes internes du PM38 -----
                for pos in lignes_pm:
                    ax.vlines(
                        x_left + pos,
                        ymin=y_top,
                        ymax=y_top + hauteur_pm,
                        colors="black",
                        linewidth=0.35,
                        zorder=16
                    )

                # ==============================
                # 🟩 ÉCROUS SPÉCIFIQUES AU PM38
                # ==============================
                if pm38_ec:
                    type_ec = pm38_ec.get("type", "M4")
                    qty = pm38_ec.get("quantite", 2)

                    couleur_ecrou = {
                        "M4": "green",
                        "M5": "blue",
                        "M6": "red",
                        "M8": "black"
                    }.get(type_ec, "gray")

                    ecrou_size = 17
                    ecart = 25  # écart vertical entre écrous

                    # centre vertical du PM
                    y_center = y_top + hauteur_pm / 2

                    # calcul vertical dynamique basé sur qty
                    offset_y = (qty - 1) * ecart / 2
                    pos_y_list = [(y_center + i * ecart) - offset_y for i in range(qty)]

                    # ===== X = VRAI BORD PM38 + 12 mm =====
                    x_ecrou = x_left + 12 - (ecrou_size / 2)

                    # dessin des écrous
                    for cy in pos_y_list:
                        y_ec = cy - ecrou_size / 2

                        ax.add_patch(patches.Rectangle(
                            (x_ecrou, y_ec),
                            ecrou_size,
                            ecrou_size,
                            facecolor=couleur_ecrou,
                            edgecolor='black',
                            linewidth=0.3,
                            zorder=30
                        ))

                        ax.add_patch(patches.Circle(
                            (x_ecrou + ecrou_size / 2, cy),
                            radius=3,
                            facecolor="grey",
                            edgecolor="black",
                            linewidth=0.3,
                            zorder=31
                        ))


    

        # Rail DIN (si présent)
        rail = elt.get("options", {}).get("rail_din", None)
        if rail and rail.get("enabled"):
            rail_x = rail["position"]
            rail_width = rail["longueur"]
            rail_height = 35
            rail_y = current_y + hauteur / 2 - rail_height / 2

            ax.add_patch(patches.Rectangle(
                (rail_x, rail_y),
                rail_width,
                rail_height,
                facecolor='gray',
                edgecolor='black',
                linewidth=0.3,
                zorder = 8
            ))

            # Hauteurs des rainures DIN35 (en mm depuis le bord haut du DIN)
            rainures_din35 = [5, 10, 25, 30]
            # --- RAINURES DIN35 (comme profils : lignes horizontales) ---
            for y_rel in rainures_din35:
                y_line = rail_y + y_rel

                ax.hlines(
                    y=y_line,
                    xmin=rail_x,
                    xmax=rail_x + rail_width,
                    color='black',
                    linewidth=0.35,
                    zorder=9
                )


            ax.text(rail_x + rail_width / 2, rail_y + rail_height / 2,
                    "DIN35", ha="center", va="center", fontsize=5.5, zorder = 10)
            

                    

        # Écrous (si présents)
        ecrou = elt.get("options", {}).get("ecrous", None)
        if ecrou:
            couleur_ecrou = {
                "M4": "green",
                "M5": "blue",
                "M6": "red",
                "M8": "black"
            }.get(ecrou.get("type"), "gray")

            nb = ecrou.get("quantite", 0)
            ecrou_size = 17
            ecart = 25

            total_width = (nb - 1) * ecart
            start_x = (largeur_profil - total_width) / 2

                               
            # ---- CALCUL SPÉCIFIQUE POUR PM50 ----
            if elt["Référence"] == "PM50":
                # Axe à 13 mm depuis le haut du PM50
                y_center = current_y + 13
                y_ecrou = y_center - ecrou_size / 2
            else:
                # comportement normal (centré)
                y_ecrou = current_y + hauteur / 2 - ecrou_size / 2

            for i in range(nb):
                x_ecrou = start_x + i * ecart
                ax.add_patch(patches.Rectangle(
                    (x_ecrou, y_ecrou),
                    ecrou_size,
                    ecrou_size,
                    facecolor=couleur_ecrou,
                    edgecolor='black',
                    linewidth=0.3,
                    zorder=9
                ))

                # Cercle transparent au centre
                cx = x_ecrou + ecrou_size / 2
                cy = y_ecrou + ecrou_size / 2

                ax.add_patch(patches.Circle(
                    (cx, cy),
                    radius=3,               # Ø6 mm
                    facecolor="grey",
                    edgecolor="black",
                    linewidth=0.3,
                    zorder=10
                ))
        # --- Cercles symétriques spécifiques au PM50 ---
        if elt["Référence"] == "PM50":
            # Position verticale du centre PM50 (comme ton code écrous)
            y_center_pm50 = current_y + 37
            cx_left = 15

            # Position droite = miroir par rapport à la largeur du châssis
            cx_right = largeur_profil - cx_left

            # Dessin des deux cercles
            for cx in [cx_left, cx_right]:
                ax.add_patch(patches.Circle(
                    (cx, y_center_pm50),
                    radius=4,
                    facecolor="#d3d3d3",
                    edgecolor="black",
                    linewidth=0.3,
                    zorder=25  # au-dessus du PM50
                ))
        # --- Cercles symétriques spécifiques au DIN35 ---
        if elt["Référence"] == "DIN35":
            # Position verticale du centre DIN35 (comme ton code écrous)
            y_center_pm50 = current_y + 17.5
            cx_left = 15

            # Position droite = miroir par rapport à la largeur du châssis
            cx_right = largeur_profil - cx_left

            # Dessin des deux cercles
            for cx in [cx_left, cx_right]:
                ax.add_patch(patches.Circle(
                    (cx, y_center_pm50),
                    radius=4,
                    facecolor="#d3d3d3",
                    edgecolor="black",
                    linewidth=0.3,
                    zorder=25  # au-dessus du DIN35
                ))




  
       
        # Décalage vertical pour l’élément suivant
        current_y += hauteur 
        if peigne_bas:
            current_y += peigne_height

    ax.set_aspect('equal')
    ax.axis("off")

    # =====================================================
    # 🔶 PROFILS VERTICAUX (profil horizontal tourné)
    # =====================================================

    verticals = st.session_state.get("verticals", [])
    peigne_h = 15  # hauteur peigne standard

    for pv in verticals:

        ref_vert     = pv.get("Référence")
        ref_capot    = pv.get("Capot")
        cote         = pv.get("Côté", "gauche")
        hauteur_vert = pv.get("Longueur", h - 100)

        # --- Largeur du profil vertical =
        #     hauteur du profil horizontal dans ton Excel
        largeur_vert = 50
        info_v = df_refs[df_refs["Référence"] == ref_vert]
        if not info_v.empty:
            largeur_vert = int(info_v["Hauteur (mm)"].values[0])

        # --- Epaisseur du capot vertical ---
        capot_ep = 30
        info_c = df_refs[df_refs["Référence"] == ref_capot]
        if not info_c.empty:
            capot_ep = int(info_c["Hauteur (mm)"].values[0])

        # Largeur totale de l'ensemble vertical
        largeur_totale_vertical = peigne_h + largeur_vert + peigne_h + capot_ep

        # --- Position X de base ---
        if cote == "gauche":
            x0 = 0
        else:
            x0 = la - largeur_totale_vertical

        # =====================================================
        #   LOGIQUE D'INVERSION (si Côté = droite)
        # =====================================================
        if cote == "gauche":
            # Ordre normal : peigne ext → profil → peigne int → capot
            x_peigne_ext = x0
            x_profil     = x0 + peigne_h
            x_peigne_int = x0 + peigne_h + largeur_vert
            x_capot      = x0 + peigne_h + largeur_vert + peigne_h

        else:
            # Ordre inversé : capot → peigne ext → profil → peigne int
            # (et peigne EXT doit toucher le montant droit)
            x_peigne_ext = la - peigne_h -100              # contre le montant droit
            x_profil     = x_peigne_ext - largeur_vert
            x_peigne_int = x_profil - peigne_h
            x_capot      = x_peigne_int - capot_ep     # vers l’intérieur

        # -------------------------------------------------
        # 🟦 PEIGNE EXTÉRIEUR (toujours contre le montant)
        # -------------------------------------------------
        ax.add_patch(patches.Rectangle(
            (x_peigne_ext, 0),
            peigne_h,
            hauteur_vert,
            facecolor=couleur_peigne,
            edgecolor='black',
            linewidth=0.2,
            zorder=50
        ))

        # -------------------------------------------------
        # 🟩 PROFIL
        # -------------------------------------------------
        ax.add_patch(patches.Rectangle(
            (x_profil, 0),
            largeur_vert,
            hauteur_vert,
            facecolor=couleur_profil,
            edgecolor='black',
            linewidth=0.3,
            zorder=51
        ))
        # ====================
        # 🔵 RAINURES VERTICALES
        # ====================
        info_v = df_refs[df_refs["Référence"] == ref_vert]

        if not info_v.empty and "Rainures Y (mm)" in info_v.columns:
            rainure_val = info_v.iloc[0]["Rainures Y (mm)"]

            if pd.notna(rainure_val):
                try:
                    positions = [float(y.strip()) for y in str(rainure_val).split(";") if y.strip()]

                    for ry in positions:
                        x_rainure = x_profil + ry

                        ax.vlines(
                            x=x_rainure,
                            ymin=0,
                            ymax=hauteur_vert,
                            colors="black",
                            linewidth=0.25,
                            zorder=55
                        )
                except:
                    pass
        # -------------------------------------------------
        # 🟧 PEIGNE INTÉRIEUR (entre profil et capot)
        # -------------------------------------------------
        ax.add_patch(patches.Rectangle(
            (x_peigne_int, 0),
            peigne_h,
            hauteur_vert,
            facecolor=couleur_peigne,
            edgecolor='black',
            linewidth=0.2,
            zorder=50
        ))

        # -------------------------------------------------
        # 🟥 CAPOT
        # -------------------------------------------------
        ax.add_patch(patches.Rectangle(
            (x_capot, 0),
            capot_ep,
            hauteur_vert,
            facecolor=couleur_capot ,
            edgecolor='black',
            linewidth=0.3,
            zorder=52
        ))
        # ==========================
        # 📝 TEXTES DES ÉLÉMENTS VERTICAUX
        # ==========================

        y_txt = -10  # au-dessus du bloc

        # Peigne extérieur
        ax.text(
            x_peigne_ext + peigne_h / 2,
            y_txt,
            "PF300",
            fontsize=6,
            rotation=90,
            va="bottom",
            ha="center",
            zorder=60
        )

        # Profil vertical
        ax.text(
            x_profil + largeur_vert / 2,
            y_txt,
            ref_vert,
            fontsize=6,
            rotation=90,
            va="bottom",
            ha="center",
            zorder=60
        )

        # Peigne intérieur
        ax.text(
            x_peigne_int + peigne_h / 2,
            y_txt,
            "PF300",
            fontsize=6,
            rotation=90,
            va="bottom",
            ha="center",
            zorder=60
        )

        # Capot vertical
        ax.text(
            x_capot + capot_ep / 2,
            y_txt,
            ref_capot,
            fontsize=6,
            rotation=90,
            va="bottom",
            ha="center",
            zorder=60
        )
    # =====================================================
    # 🔵 AFFICHAGE FINAL DU VISUEL
    # =====================================================
    if show:
       st.markdown(f"### {t('apercu_chassis')}")
       st.pyplot(fig)
    return fig

# Generer le visuel au format image # SOUS PROGRAMME #
def generer_visuel_image(h, la):
    buf = BytesIO()
    fig = visuel_chassis(h, la, show=False)  # Tu dois modifier ta fonction pour accepter show=False
    fig.savefig(buf, format='PNG', dpi=300, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

# Generer le PDF récapitulatif # SOUS PROGRAMME #
def generer_pdf(empilage,):
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    logo_path = ("logo.jpg")
    logo = ImageReader(logo_path)
    c.drawImage(logo, x=425, y=752, width=150, height=100, preserveAspectRatio=True, mask='auto')

    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, t("recap_projet_txt"))
    y -= 30


    c.setFont("Helvetica", 12)
    c.drawString(40, y, f"{t("reference_projet_txt")} : {st.session_state.get('ref_projet', '—')}")
    y -= 30
    c.drawString(40, y, f"{t("commentaire_projet_txt")} : {st.session_state.get('commentaire_projet', '—')}")
    y -= 30
    c.drawString(40, y, f"{t("marque_arm_txt")} : {st.session_state.get('marq_arm', '—')}")
    y -= 30
    c.drawString(40, y, f"{t("reference_arm_txt")} : {st.session_state.get('ref_arm', '—')}")
    y -= 30
    c.drawString(40, y, f"{t("hauteur_de_armoire_txt")} : {st.session_state.get('hau_arm', '—')}")
    y -= 30
    c.drawString(40, y, f"{t("largeur_de_armoire_txt")} : {st.session_state.get('lar_arm', '—')}")

    # Inserer image du visuel #
   
    img_buffer = generer_visuel_image(h, la)
    image = ImageReader(img_buffer)
    iw, ih = image.getSize()
    # ratio de redimensionnement
    max_width = 250
    scale = max_width / iw
    new_height = ih * scale

    c.drawImage(image, x=40, y=0, width=max_width, height=new_height)


    c.showPage() #page suivante #
    c.drawImage(logo, x=425, y=752, width=150, height=100, preserveAspectRatio=True, mask='auto')
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, t("tableau_empilage_txt"))
    y = 770
    for i, elt in enumerate(empilage):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"{i+1}. {elt['Référence']} - {elt['Hauteur (mm)']} mm")
        y -= 15
        c.setFont("Helvetica", 10)

        options = elt.get("options", {})
        commentaires = elt.get("commentaire", "")
        
        if "peigne_haut" in elt and elt["peigne_haut"]:
            c.drawString(60, y, f"- {t("peigne_haut_active")}")
            y -= 15
        if "peigne_bas" in elt and elt["peigne_bas"]:
            c.drawString(60, y, f"- {t("peigne_bas_active")}")
            y -= 15
        if "rail_din" in options:
            rail = options["rail_din"]
            c.drawString(60, y, f"- {t("rail_din_txt")} : {rail['longueur']} mm - {rail['position']} mm {t("bord_gauche")}")
            y -= 15
        if "ecrous" in options:
            ec = options["ecrous"]
            c.drawString(60, y, f"- {t("ecrous_txt")} : {ec['type']} x{ec['quantite']}")
            y -= 15
        if "pm_verticale" in options:
            pm = options["pm_verticale"]
            c.drawString(60, y, f"- PM38 : {pm['longueur']} mm - {pm['position']} mm {t("bord_gauche")} - {t("entraxe_seul_txt")} : {pm['entraxe']}")
            y -= 15


        if commentaires:
            c.drawString(60, y, f"- {t("commentaire_seul_txt")} : {commentaires}")
            y -= 15

        y -= 10
        if y < 60:
            c.showPage()
            y = height - 40

    c.save()
    buffer.seek(0)
    return buffer

# Sauvegarder le projet #
def save_projet(retourner_json=False):
    projet = {
        "hau_arm": st.session_state.get("hau_arm"),
        "lar_arm": st.session_state.get("lar_arm"),
        "marq_arm": st.session_state.get("marq_arm", ""),
        "ref_arm": st.session_state.get("ref_arm", ""),
        "ref_projet": st.session_state.get("ref_projet", ""), 
        "commentaire_projet": st.session_state.get("commentaire_projet", ""),
        "empilage": st.session_state.get("empilage", []),
        "verticals": st.session_state.get("verticals", []), 
        "etrier": st.session_state.get("etrier"),
        "montant": st.session_state.get("montant"),
        "couleur_pc": st.session_state.get("couleur_pc", "Bleu"), 
    }
    if retourner_json:
        return projet  # <— on peut le réutiliser pour la sauvegarde locale !

    buffer = io.StringIO()
    json.dump(projet, buffer, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 Télécharger le projet",
        data=buffer.getvalue(),
        file_name="projet.json",
        mime="application/json"
    )

# Charger le projet #
def charger_projet():

    uploaded = st.sidebar.file_uploader("📂 Charger un projet", type=["json"])
    if uploaded:
        data = json.load(uploaded)
        st.session_state["hau_arm"] = data.get("hau_arm")
        st.session_state["lar_arm"] = data.get("lar_arm")
        st.session_state["marq_arm"] = data.get("marq_arm", "")
        st.session_state["ref_arm"] = data.get("ref_arm", "")
        st.session_state["ref_projet"] = data.get("ref_projet", "")
        st.session_state["commentaire_projet"] = data.get("commentaire_projet", "")
        st.session_state["empilage"] = data.get("empilage", [])
        st.session_state["verticals"] = data.get("verticals", [])
        st.session_state["etrier"] = data.get("etrier")
        st.session_state["montant"] = data.get("montant")
        st.session_state["couleur_pc"] = data.get("couleur_pc", "Bleu")
        st.success("Projet chargé avec succès ✅")

def local_projet ():
        # ------------------------------------------------
    # 0) Flags internes Streamlit
    # ------------------------------------------------
    if "resetting" not in st.session_state:
        st.session_state.resetting = False

    if "restored" not in st.session_state:
        st.session_state.restored = False


    # ------------------------------------------------
    # 1) Bouton RESET (clic utilisateur)
    # ------------------------------------------------
    reset = st.sidebar.button("🔄 Réinitialiser le projet")

    if reset:
        # On marque qu'un reset est en cours
        st.session_state.resetting = True

        # On relance Python proprement pour entrer dans le mode reset
        st.rerun()


    # ------------------------------------------------
    # 2) Quand le script revient juste après un reset
    # ------------------------------------------------
    if st.session_state.resetting:

        # ⚠️ On affiche quelque chose pour forcer Streamlit à envoyer du HTML
        st.write("🔁 Réinitialisation du projet…")

        # ⚠️ Maintenant on peut exécuter du JS PROPREMENT
        streamlit_js_eval(
            js_expressions="""
                // Suppression complète
                localStorage.removeItem('sauvegarde_projet');
                localStorage.clear();
                sessionStorage.clear();

                // Rechargement propre
                setTimeout(() => { window.location.reload(); }, 150);
            """,
            want_output=False
        )

        st.stop()  # On arrête Python


    # ------------------------------------------------
    # 3) Charger la sauvegarde locale AU DÉMARRAGE
    # ------------------------------------------------
    saved_json = streamlit_js_eval(
        js_expressions="localStorage.getItem('sauvegarde_projet');",
        want_output=True
    )


    # ------------------------------------------------
    # 4) Restauration unique (évite les problèmes de double charge)
    # ------------------------------------------------
    if saved_json and not st.session_state.restored:
        try:
            data = json.loads(saved_json)
            for key, value in data.items():
                st.session_state[key] = value
            st.session_state.restored = True
        except:
            pass
 
def options_chassis():
    # ---- OPTIONS DU CHÂSSIS ----
    with st.sidebar.expander("⚙️ Options du châssis", expanded=False):
         # --- COULEUR PEIGNES & CAPOTS ---
         st.markdown("### Couleur peignes et capots")

         couleur_pc = st.radio(
             "Choisissez la couleur :",
             ["Bleu", "Gris"],
             index=["Bleu", "Gris"].index(st.session_state.get("couleur_pc", "Bleu")),
             key="couleur_pc"
         ) 

        # --- CHOIX D'ÉTRIER ---
         st.markdown("### Choix d'étrier")
         etrier = st.radio(
                "Sélectionnez un étrier :",
                ["EM45", "EM80", "EM90"],
                index=["EM45", "EM80", "EM90"].index(st.session_state["etrier"]),
                key="etrier"
            )
        # --- CHOIX DU MONTANT  ---
         st.markdown("### Choix des montants")
         etrier = st.radio(
                "Sélectionnez un montant :",
                ["MSF12", "MSF35", "MDF45"],
                index=["MSF12", "MSF35", "MDF45"].index(st.session_state["montant"]),
                key="montant"
            )



         if "verticals" not in st.session_state:
            st.session_state.verticals = []

         if st.button("➕ Ajouter un profil vertical", key="add_vert_sidebar"):
            # Crée un profil vertical vide
            st.session_state.verticals.append({
                "Type": "PP (flat)",
                "Référence": None,
                "Capot": "CPF30",
                "Côté": "gauche",
                "Longueur": st.session_state.get("hau_arm", 2000)-100
            })
            st.rerun()
        
def tableau_vertical():

    st.markdown("## 📐 Profils verticaux")

    # Si aucun profil vertical → message simple
    if "verticals" not in st.session_state or len(st.session_state.verticals) == 0:
        st.info("Aucun profil vertical ajouté.")
        return

    # Liste des verticals
    for i, vert in enumerate(st.session_state.verticals):

        st.subheader(f"Profil vertical {i+1}")

        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])

        # --- TYPE ---
        with col1:
            # Types autorisés explicitement
            type_options = ["PP (flat)", "PPA (DIN rail)"]

            # Correction automatique si projet contient un type non autorisé
            type_init = vert["Type"] if vert["Type"] in type_options else "PP (flat)"

            type_sel = st.selectbox(
                "Type",
                type_options,
                index=type_options.index(type_init),
                key=f"vtype_{i}"
            )

            vert["Type"] = type_sel

        # --- RÉFÉRENCE ---
        with col2:
            ref_options = df_refs[df_refs["Type"] == type_sel]["Référence"].tolist()
            ref_sel = st.selectbox(
                "Référence",
                ref_options,
                index=ref_options.index(vert["Référence"]) if vert["Référence"] in ref_options else 0,
                key=f"vref_{i}"
            )
            vert["Référence"] = ref_sel

        # --- CAPOT ---
        with col3:
            capot_options = df_refs[df_refs["Type"] == "CPF"]["Référence"].tolist()
            capot_sel = st.selectbox(
                "Capot",
                capot_options,
                index=capot_options.index(vert["Capot"]) if vert["Capot"] in capot_options else 0,
                key=f"vcap_{i}"
            )
            vert["Capot"] = capot_sel

        # --- CÔTÉ ---
        with col4:
            cote_sel = st.selectbox(
                "Côté",
                ["gauche", "droite"],
                index=0 if vert["Côté"] == "gauche" else 1,
                key=f"vcot_{i}"
            )
            vert["Côté"] = cote_sel

        # --- SUPPRESSION ---
        with col5:
            if st.button("🗑️", key=f"vdel_{i}"):
                st.session_state.verticals.pop(i)
                st.rerun()

        # --- Longueur ---
        vert["Longueur"] = st.number_input(
            "Longueur (mm)",
            min_value=50,
            max_value=5000,
            step=10,
            value=vert["Longueur"],
            key=f"vlen_{i}"
        )        


def export_dxf_from_figure(fig, filename="chassis_export.dxf"):
    """Exporte toutes les formes visibles du visuel Matplotlib en DXF."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    for ax in fig.get_axes():

        # --- Lignes (rainures, PM38, axes…) ---
        for line in ax.lines:
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            for i in range(len(xdata) - 1):
                msp.add_line(
                    (float(xdata[i]), float(-ydata[i])),
                    (float(xdata[i+1]), float(-ydata[i+1]))
                )

        # --- Rectangles / Shapes (profils, peignes, PM38, rails...) ---
        for patch in ax.patches:

            if isinstance(patch, Rectangle):
                x, y = patch.get_xy()
                w, h = patch.get_width(), patch.get_height()

                # rectangle = 4 segments DXF
                pts = [
                    (x, -y),
                    (x + w, -(y)),
                    (x + w, -(y + h)),
                    (x, -(y + h)),
                    (x, -y)
                ]
                msp.add_lwpolyline(pts, close=True)

            elif isinstance(patch, Circle):
                cx, cy = patch.center
                r = patch.get_radius()
                msp.add_circle((cx, -cy), r)

    doc.saveas(filename)
    return filename

def generer_dxf(fig):
    dxf_path = export_dxf_from_figure(fig)

    # Lecture du fichier DXF
    with open(dxf_path, "rb") as f:
        dxf_bytes = f.read()

    st.download_button(
        label="📐 Télécharger DXF",
        data=dxf_bytes,
        file_name="chassis_export.dxf",
        mime="image/vnd.dxf"
    )





######## Programme principale MAIN #########

trads = charger_traductions()
local_projet()

# Configuration du haut de page #

st.set_page_config(page_title="Configurateur Châssis", layout="wide")
st.title(t("titre_application"))

initialisation_infos_client()

# Charger et lire base de donée excel avec les réferences #
df_refs = charger_base()
if "empilage" not in st.session_state:
    st.session_state.empilage = []


charger_projet()

choix_langue()

h,la = infos_clients()

selection_empillage()  

options_chassis()

tableau_empillage(h)

tableau_vertical()

options_profils()

fig =visuel_chassis(h,la,)

generer_dxf(fig)

pdf_buffer = generer_pdf(
    st.session_state.empilage,
   
)

st.download_button(
    label=(t("telecharger_pdf_txt")),
    data=pdf_buffer,
    file_name="recapitulatif_chassis.pdf",
    mime="application/pdf"
)

save_projet()

projet_clean = save_projet(retourner_json=True)

streamlit_js_eval(
    js_expressions=f"""
        localStorage.setItem('sauvegarde_projet', JSON.stringify({json.dumps(projet_clean)}));
    """,
    want_output=False
)