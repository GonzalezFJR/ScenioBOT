import telepot
import os, time, sys, random, json, time, datetime

from generate_card import generate_card

PART_LIST = 'part_list.json'
MISIONS = 'misions.txt'
STATE = 'state.json'
LOGFILE = 'log.txt'

TOKEN = 'token_test.txt'
MASTER = 574837872



def Log(msg, print_msg=True, type='msg', name=None):
    ''' Log a message '''
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = ''
    if type is not None:
        header += f'[{date}] [{type.upper()}] '
    if name is not None:
        header += f'({name}) >> '
    with open(LOGFILE, 'a', encoding='utf-8') as f:
        f.write(header + msg+'\n')
    if print_msg:
        print(header + msg)

def AddPart(ID, name):
    ''' Añade un participante '''
    if not os.path.exists(PART_LIST):
        with open(PART_LIST, 'w') as f:
            json.dump({}, f)
    with open(PART_LIST, 'r') as f: part_list = json.load(f)
    if str(ID) in part_list:
        return False
    part_list[ID] = name
    with open(PART_LIST, 'w') as f: json.dump(part_list, f)
    return True

def GetPartName(ID):
    ''' Obtiene el nombre de un participante '''
    with open(PART_LIST, 'r') as f:
        part_list = json.load(f)
    IDs, names = list(part_list.keys()), list(part_list.values())
    if ID in names:
        return ID # ID is actually the name	
    elif ID in IDs:
        return part_list[ID]
    return None

def GetPartID(name):
    ''' Obtiene el ID de un participante '''
    with open(PART_LIST, 'r') as f:
        part_list = json.load(f)
    name = str(name)
    IDs, names = list(part_list.keys()), list(part_list.values())
    if name in IDs:
        return name # name is actually the ID
    elif name in names:
        for ID in part_list:
            if part_list[ID] == name:
                return ID
    return None

##########################################
### Create initial state

def CreateGame():
    ''' Crea un juego nuevo '''
    with open(PART_LIST, 'r') as f:
        part_list = json.load(f)
        npart = len(part_list)
    with open(MISIONS, 'rt', encoding='utf-8') as f:
        misions = f.readlines()
        misions_orig = misions.copy()
        while len(misions) < npart:
            # duplicate some misions randomly
            misions.append(random.choice(misions_orig))
        random.shuffle(misions)
    skills = ['reencarnacion', 'posesion', 'venganza', 'intercambio', 'superviviente', 'redencion', 'traicion', 'fantasma', 'demonio', 'saboteador']
    state = {}
    partcipantes = [part_list[ID] for ID in part_list]
    skills = skills*(len(partcipantes)//len(skills) + 1)
    random.shuffle(skills)
    for i, p in enumerate(partcipantes):
        obj = partcipantes[(i+1)] if i < (npart-1) else partcipantes[0]
        state[p] = {'mision': misions.pop(), 'objetivo': obj, 'status': True, 'list_of_kills': [], 'killed_by': None, 'killed_by_mision':None, 'nmisions': 0, 'n_mision_joker': 3, 'skill': skills.pop(),
                    'mision_done':False, 'dead_report':False, 'skill_avail':True, 'reencarnation':None}
    with open(STATE, 'w') as f: json.dump(state, f)
    Log(f'Juego creado con {npart} participantes', type='EVT')
    return state

def AddPlayer(name, mision=None, objetivo=None, nJoker=None):
    ''' Añade un jugador al juego '''
    with open(STATE, 'r') as f:
        state = json.load(f)
    if name in state and state[name]['status']:
        Log(f'No se puede añadir a jugador {name}: ya está en el juego y vivo', type='EVT')
        return False
    if mision is None:
        mision = GetANewRandomMision()
    state[name] = {'mision': mision, 'objetivo': objetivo, 'status': True, 'list_of_kills': [], 'killed_by': None, 'killed_by_mision':None, 'nmisions': 0, 'n_mision_joker': 3, 'skill': None, 'mision_done':False, 'dead_report':False, 'skill_avail':True, 'reencarnation':None}
    with open(STATE, 'w') as f: json.dump(state, f)
    Log(f'Jugador {name} añadido al juego' + f"con objetivo {objetivo}" if objetivo is not None else '', type='EVT')
    return True

def ReencarnatePlayer(name, obj, asesino=None, mision=None):
    ''' El jugador reencarnado tiene que matar a obj '''
    with open(STATE, 'r') as f: state = json.load(f)
    state[name]['status'] = True
    state[name]['objetivo'] = obj
    if asesino is not None:
        state[asesino]['objetivo'] = name
    if mision is None:
        mision = GetANewRandomMision()
    with open(STATE, 'w') as f: json.dump(state, f)
    Log(f'El jugador {name} se ha vuelo al juego, teniendo que matar a {obj}')
    return True

def GetANewRandomMision(otherthan=None):
    ''' Obtiene una nueva misión aleatoria '''
    with open(MISIONS, 'rt', encoding='utf-8') as f:
        misions = f.readlines()
    new = random.choice(misions)
    if otherthan is not None:
        while new == otherthan:
            new = random.choice(misions)
    return new

##########################################
### Actions and game functions
def GetAssasinsOf(obj):
    ''' Devuelve una lista con los asesinos de un objetivo '''
    with open(STATE, 'r') as f: state = json.load(f)
    assasins = []
    for name in state:
        if state[name]['objetivo'] == obj:
            assasins.append(name)
    return assasins


class GameUpdate:

    def __init__(self, bot):
        self.bot = bot
        self.alarm25 = False
        self.alarm10 = False
        self.alarm5 = False

    def Msg(self, name, msg):
        ''' Envia un mensaje a un jugador '''
        self.bot.sendMsg(name, msg)

    def Img(self, name, imgpath):
        ''' Envia una imagen a un jugador '''
        self.bot.sendImg(name, imgpath)

    ##########################################
    ### Reports and checks 
    def ReportedCompleteMision(self, name):
        ''' Un jugador reporta que ha completado la misión - se actualiza su etiqueta '''
        with open(STATE, 'r') as f: state = json.load(f)
        if not state[name]['status']: return False
        state[name]['mision_done'] = True
        with open(STATE, 'w') as f: json.dump(state, f)
        Log(f"{name} reporta misión completada", type='EVT')
        return True

    def ReportedDead(self, name, killed_by=None):
        ''' Un jugador reporta que ha muerto - se actualiza su etiqueta '''
        with open(STATE, 'r') as f: state = json.load(f)
        if not state[name]['status']: return False
        state[name]['dead_report'] = True
        state[name]['killed_by'] = killed_by
        if killed_by is not None:
            state[name]['killed_by_mision'] = state[killed_by]['mision']
        with open(STATE, 'w') as f: json.dump(state, f)
        Log(f"{name} reporta muerte", type='EVT')
        return True

    def CheckMisionCompleted(self, ase=None, obj=None):
        ''' Check si ambos reportaron y, si es así, ejecuta Nest. No actualiza state. '''
        with open(STATE, 'r') as f: state = json.load(f)
        if ase is not None:
            if not state[ase]['status']: return
            obj = state[ase]['objetivo']
            if state[ase]['mision_done'] and state[obj]['dead_report']:
                Log(f'Misión completada y reportada por el asesino {ase} y el objetivo {obj}', type='EVT')
                self.Next(ase, obj)
                return True
            else:
                Log(f'Falta por reportar uno de los dos: {ase}, {obj}', type='EVT')
                return False
        elif obj is not None:
            if not state[obj]['status']: return
            assas = GetAssasinsOf(obj)
            ase = None
            for _ase in assas:
                if state[_ase]['mision_done']:
                    ase = _ase 
            if ase is not None and state[ase]['mision_done'] and state[obj]['dead_report']:
                Log(f'Misión completada y reportada por el asesino {ase} y el objetivo {obj}', type='EVT')
                self.Next(ase, obj)
                return True
            else:
                Log(f'Falta por reportar uno de los dos: {ase}, {obj}', type='EVT')
                return False
        else:
            return False 

    #################################
    ### Funciones para alguna de las habilidades
    def Intercambio(self, obj):
        ''' Produce un intercambio de obj por un random... return de ese random ''' 
        with open(STATE, 'r') as f: state = json.load(f)
        # A → B → C → … → W → X → Y → …
        As = GetAssasinsOf(obj)
        X = random.choice([name for name in state if state[name]['status'] and name != obj])
        Y = state[X]['objetivo']
        Ws = GetAssasinsOf(X)
        B = obj
        C = state[B]['objetivo']
        # A → X → C → … → W → B → Y → …  
        state[X]['objetivo'] = C
        self.Msg(X, f'¡ATECIÓN! Alguien ha usado una habilidad y ahora tu objetivo es {C}... ignora a tu anterior objetivo. La misión es la misma.')
        for W in Ws:
            state[W]['objetivo'] = B
            self.Msg(W, f"¡ATENCIÓN! Alguien ha usado una habilidad y ahora tu objetivo es {B}... ignora a tu anterior objetivo. La misión es la misma.")
        state[obj]['objetivo'] = Y
        self.Msg(B, f'Ahora tu objetivo es {obj}')
        # the state of ase is not changed in this function!
        with open(STATE, 'w') as f: json.dump(state, f)
        return X

    ################################
    ### Funciones del juego. Actualizan etiquetas de objetivos y misiones...

    def CompleteMision(self, name, newObj=None, randomMision=False):
        ''' Completa la misión actual
            Añade el objetivo a la lista de kills
            Hereda misión y objetivo.
        '''
        with open(STATE, 'r') as f: state = json.load(f)
        if not state[name]['status']: return
        prev_obj = state[name]['objetivo']
        state[name]['nmisions'] += 1
        state[name]['list_of_kills'].append(prev_obj)
        state[name]['mision'] = state[prev_obj]['mision'] if not randomMision else GetANewRandomMision()
        state[name]['objetivo'] = state[prev_obj]['objetivo'] if newObj is None else newObj
        state[name]['mision_done'] = False
        with open(STATE, 'w') as f: json.dump(state, f)
        Log(f"{name} ha completado la misión. Lleva {state[name]['nmisions']} misiones completadas.", type='EVT')
        return True

    def Dead(self, name, killed_by=None):
        ''' Mata a un jugador y actualiza su estado, pero no el de ningún otro jugador... '''
        with open(STATE, 'r') as f: state = json.load(f)
        if not state[name]['status']: return
        state[name]['status'] = False
        state[name]['killed_by'] = killed_by
        if killed_by is not None:
            state[name]['killed_by_mision'] = state[killed_by]['mision']
        with open(STATE, 'w') as f: json.dump(state, f)
        Log(f"{name} ha sido matado por {killed_by}... y ha sido finalmente declarado muerto", type='EVT')
        return None

    def Next(self, ase, obj):
        ''' Ejecuta los siguientes pasos tras completarse una misión... primero, mira la habilidad del objetivo, y si no, actualiza los estados '''
        with open(STATE, 'r') as f:
            state = json.load(f)

        # Comprobar si hay alguna reencarnacion
        sel_obj = None
        randomMision = False
        if state[obj]['reencarnation'] is not None:
            ren = state[obj]['reencarnation']
            prev_obj = state[obj]['objetivo']
            if state[obj][skill] == "traicion":
                if not 'helping' in state[obj]:
                    Log('No se ha encontrado el ayudante de {obj}...', type='ERROR')
                else:
                    prev_obj = state[obj]['helping']
            else:
                sel_obj = ren
            time.sleep(0.1)
            ReencarnatePlayer(ren, prev_obj)

        # Primero, comprueba la skill del muerto y actualiza es state
        if state[obj]['skill_avail']:
            state[obj]['skll_avail'] = False
            state[obj]['dead_report'] = False
            with open(STATE, 'w') as f: json.dump(state, f)
            skill = state[obj]['skill'].lower()

            if  skill == 'reencarnacion':
                random_live = random.choice([name for name in state if state[name]['status'] and name != obj])
                state[random_live]['reencarnation'] = obj
                state[obj]['status'] = False
                with open(STATE, 'w') as f: json.dump(state, f)
                msg = "Acabas de morir. Tu habilidad es Reencarnación. Puedes volver al juego cuando un jugador, que aún sigue con vida, muera. No obstante, no sabes cuál es ese jugador… nadie lo sabe. Mantén la atención, te avisaré cuando suceda."
                self.Msg(obj, msg)
                Log(f"El objetivo {obj} ha usado reencarnacion y ahora {random_live} está poseído.", type='HAB')
                
            elif skill == "posesion":
                state[ase]['reencarnation'] = obj
                state[obj]['status'] = False
                with open(STATE, 'w') as f: json.dump(state, f)
                msg = "Acabas de morir. Tu habilidad de Posesión. Posees al jugador que te mató, y volverás al juego cuando ese jugador muera. Sigue prestándome atención, ya que el juego aún no ha terminado para ti."
                self.Msg(obj, msg)
                Log(f"El objetivo {obj} ha usado posesion y ahora {ase} está poseído.", type='HAB')

            elif skill == 'venganza':
                msg = "Acabas de morir. Tu habilidad especial es Venganza. El juego no ha acabado para ti. Tienes una nueva misión, encaminada a matar a tu asesino. Si lo consigues, podrás seguir jugando."
                state[obj]['mision'] = GetANewRandomMision()
                state[obj]['objetivo'] = ase
                change_objs = GetAssasinsOf(ase)
                for name in change_objs:
                    state[name]['objetivo'] = obj
                with open(STATE, 'w') as f: json.dump(state, f)

                self.Msg(obj, msg)
                self.Msg(obj, CraftMisionMsg(obj))
                Log(f"El objetivo {obj} ha usado venganza y ahora tiene que matar a {ase}", type='HAB')
                for name in change_objs:
                    self.Msg(name, f"¡ATENCIÓN! El objetivo de tu misión ha cambiado. Ahora tiene que matar a {obj}.")
                    self.Msg(name, CraftMisionMsg(name))
                    Log(f"El objetivo {name} ha cambiado a {obj} (debido a un uso de venganza)", type='HAB')

            elif skill == 'intercambio':
                msg = "Acabas de morir. Tu habilidad especial es Intercambio. En tu lecho de muerte tu espíritu se cambió con el de otra persona, aún viva. Tienes que terminar la misión de este personaje. Si lo logras, podrás seguir jugando."
                state[obj]['mision'] = GetANewRandomMision()
                with open(STATE, 'w') as f: json.dump(state, f)
                some_random = self.Intercambio(obj)
                self.Msg(obj, msg)
                self.Msg(obj, CraftMisionMsg(obj))
                Log(f"El objetivo {obj} ha usado intercambio y ha habido algunos cambios. El random es {some_random}", type='HAB')

                sel_obj = some_random
                
            elif skill == 'superviviente':
                msg = "Acabas de NO morir. Tu habilidad es Superviviente. Has sobrevivido. Pero no tendrás la misma suerte la próxima vez. Vigila tus espaldas, no sabes quién te va a querer matar ni cómo. No obstante, continúa con tu misión."
                self.Msg(obj, msg)
                Log(f"El objetivo {obj} ha usado superviviente y ahora {ase} tiene que matarlo de nuevo", type='HAB')

                self.Msg(ase, f"¡ATENCIÓN! Tu objetivo ha usado su habilidad de superviviente. No ha muerto, pero no sabe que tú sigues siendo su asesino... necesitas realizar otra misión para matarlo. Si lo consigues, cuenta como una muerte doble por tu parte ;-)")
                sel_obj = obj
                randomMision = True
                
            elif skill == 'redencion':
                msg = "Acabas de morir. Sin embargo el juego no ha acabado para ti. Tu habilidad es Redención. Puedes ayudar al asesino de tu asesino a completar su misión. Si lo logras, podrás continuar jugando."
                to_help = GetAssasinsOf(ase)[0]
                state[ase]['reencarnation'] = obj
                state[obj]['helping'] = to_help
                state[obj]['status'] = False
                with open(STATE, 'w') as f: json.dump(state, f)
                self.Msg(obj, msg)
                self.Msg(obj, f'El asesino de {ase} es {to_help}. Ayúdalo a completar su misión y podrás volver al juego.')
                Log(f"El objetivo {obj} ha usado redencion y ahora tiene que ayudar a {to_help}", type='HAB')

            elif skill == 'traicion':
                msg = "Acabas de morir. Sin embargo el juego no ha acabado para ti. Tu habilidad es Traición. Puedes ayudar al asesino de tu asesino a completar su misión. Si lo logras, deberás matar también al asesino de tu asesino, con una misión te será desvelada (¡él o ella no lo sabe!). Si lo logras, podrás continuar jugando."
                to_help = GetAssasinsOf(ase)[0]
                state[ase]['reencarnation'] = obj
                state[obj]['helping'] = to_help
                state[obj]['status'] = False
                with open(STATE, 'w') as f: json.dump(state, f)
                self.Msg(obj, msg)
                self.Msg(obj, f'El asesino de {ase} es {to_help}. Ayúdalo a completar su misión (y luego le traicionarás, pero no le digas nada...).')
                Log(f"El objetivo {obj} ha usado traicion y ahora tiene que ayudar a {to_help}", type='HAB')

            elif skill == 'fantasma':
                msg = "Acabas de morir. Tu habilidad es Fantasma. Ya no puedes ganar el juego, pero puedes ayudar a que gane una persona. Si esa persona gana, podrás considerarlo una victoria moral por tu parte."
                random_live = random.choice([name for name in state if state[name]['status'] and name != obj])
                self.Msg(obj, msg)
                self.Msg(obj, f'Tu objetivo para el resto del juego es ayudar a {random_live} a conseguir su misión actual. Eso sí, debes de hacerlo con sigilo... él/ella no sabe que tú le vas a ayudar.')
                time.sleep(0.1)
                self.Msg(obj, f'La misión de {random_live} es:')
                self.Msg(obj, state[random_live]['mision'])
                self.Msg(obj, f'Y su objetivo es:')
                self.Msg(obj, state[random_live]['objetivo'])
                time.sleep(0.1)
                Log(f"El objetivo {obj} ha usado fantasma y ahora tiene que ayudar a {random_live}", type='HAB')

            elif skill == 'demonio':
                msg = "Acabas de morir. Tu habilidad es Demonio. Ya no puedes ganar el juego, pero puedes continuar jugando un poco más. Hay dos personajes que siguen vivos, pero quieres cambiar esa situación. Ayúdalos a morir."
                two_lives = [name for name in state if state[name]['status'] and name != obj]
                random.shuffle(two_lives)
                try:
                    dem1 = two_lives[0]
                    dem2 = two_lives[1]
                    ase_dem1 = GetAssasinsOf(dem1)[0]
                    ase_dem2 = GetAssasinsOf(dem2)[0]
                    mis_dem1 = state[ase_dem1]['mision']
                    mis_dem2 = state[ase_dem2]['mision']
                except:
                    Log(f"El objetivo {obj} ha usado demonio pero no se ha podido ejecutar", type='ERROR')
                self.Msg(obj, msg)
                self.Msg(obj, f'Tus objetivos para el resto del juego son fastidiar a {dem1} y a {dem2} haciendo que sus asesinos los maten. Eso sí, debes de hacerlo con sigilo... ellos no saben que tú les vas a chinchar. Y sus asesinos tampoco saben nada.')
                self.Msg(obj, f'La misión para matar a {dem1} es:')
                self.Msg(obj, mis_dem1)
                self.Msg(obj, f'La misión para matar a {dem2} es:')
                self.Msg(obj, mis_dem2)
                self.Msg(obj, f'Recuerda que no sabes quiénes deben matar a {dem1} y a {dem2}, pero sabes qué misiones tienen que hacer... y tú tienes que ayudar a que se cumplan.')
                self.Msg(obj, 'Buena suerte!')
                Log(f"El objetivo {obj} ha usado demonio y ahora tiene que ayudar a matar a {dem1} y a {dem2}", type='HAB')
                    
            elif skill == 'saboteador':
                msg = "Acabas de morir. Tu habilidad es Saboteador. Ya no puedes ganar el juego, pero puedes continuar jugando un poco más. Como buen saboteador, te has enterado de estas misiones y vas a intentar sabotearlas. Apáñatelas como puedas, y mucha suete."
                three_lives = [name for name in state if state[name]['status'] and name != obj]
                random.shuffle(three_lives)
                try:
                    dem1 = three_lives[0]
                    dem2 = three_lives[1]
                    dem3 = three_lives[2]
                    mis1 = state[dem1]['mision']
                    mis2 = state[dem2]['mision']
                    mis3 = state[dem3]['mision']
                except:
                    Log(f"El objetivo {obj} ha usado saboteador pero no se ha podido ejecutar", type='ERROR')

                self.Msg(obj, msg)
                self.Msg(obj, f'Tus objetivos para el resto del juego son fastidiar las misiones actuales de {dem1}, {dem2} y {dem3}. Eso sí, debes de hacerlo con sigilo... ellos no saben que tú les vas a chinchar.')
                self.Msg(obj, f'La misión de {dem1} es:')
                self.Msg(obj, mis1)
                self.Msg(obj, f'La misión de {dem2} es:')
                self.Msg(obj, mis2)
                self.Msg(obj, f'La misión de {dem3} es:')
                self.Msg(obj, mis3)
                self.Msg(obj, f'Recuerda que no sabes quiénes deben matar a {dem1}, {dem2} y {dem3}, pero sabes qué misiones tienen que hacer... y tú tienes que ayudar a que no se cumplan.')
                self.Msg(obj, 'Buena suerte!')
                Log(f"El objetivo {obj} ha usado saboteador y ahora tiene que sabotear a {dem1}, {dem2} y {dem3}", type='HAB')

            self.CompleteMisionAndReport(ase, newObj=sel_obj, randomMision=randomMision)

        else:
            Log(f"El objetivo {obj} no tiene habilidad disponible... ha sido matado por {ase}. Vamos a actualizar el juego e informarles.", type="EVT")
            self.Dead(obj, killed_by=ase)
            self.Msg(obj, f'Bien jugado, {obj}!')

            self.CompleteMisionAndReport(ase, newObj=sel_obj, randomMision=randomMision)
        self.CheckAndReport()
            
    #########################################################
    ### Otras funciones del juego 

    def CompleteMisionAndReport(self, name, newObj=None, randomMision=False):
        ''' Completa la misión actual y reporta '''
        self.CompleteMision(name, newObj=newObj, randomMision=randomMision)
        self.Msg(name, f'Muy bien, {name}, a por la siguien misión!')
        self.Msg(name, CraftMisionMsg(name)+'\n¡Suerte!')
        time.sleep(0.3)
        card_name = GenerateCard(name)
        time.sleep(0.5)
        self.Img(name, card_name)
        time.sleep(0.5)
        Log(f"{name} ha completado la misión y reportado", type='EVT')

    def Retire(self, name):
        ''' Retira a un jugador y actualiza su estado,
            y también hace que los jugadores que tenían como objetivo al jugador retirado hereden el objetivo del jugador retirado '''
        with open(STATE, 'r') as f: state = json.load(f)
        if not state[name]['status']: return
        state[name]['status'] = False
        state[name]['killed_by'] = 'retire'
        state[name]['killed_by_mision'] = 'retire'
        Log(f"{name} se retira del juego", type='EVT')
        assasins = GetAssasinsOf(name)
        for ass in assasins:
            if not state[ass]['status']: continue
            state[ass]['objetivo'] = state[name]['objetivo']
            self.Msg(ass, f'ATENCIÓN - Tu objetivo {name} se ha retirado... tienes un nuevo objetivo: {state[name]["objetivo"]}')
            Log(f"{ass} hereda el objetivo de {name}", type='EVT')
        with open(STATE, 'w') as f: json.dump(state, f)
        self.Msg(name, f"Gracias por haber participado, {name}. Siento mucho que te vayas... espero que hayas disfrutado del juego.")
        return True

    def Joker(self, name):
        ''' Cambia la misión y resta un joker '''
        with open(STATE, 'r') as f: state = json.load(f)
        if not state[name]['status']: 
            self.Msg(name, "Estás muerto!")
            return
        njo = state[name]['n_mision_joker']
        if njo < 1:
            Log(f"{name} no tiene comodines", type='EVT')
            self.Msg(name, "No tienes comodines!")
            return
        state[name]['n_mision_joker'] -= 1
        state[name]['mision'] = GetANewRandomMision(otherthan=state[name]['mision'])
        with open(STATE, 'w') as f: json.dump(state, f)
        Log(f"{name} ha usado un comodín. Le quedan {state[name]['n_mision_joker']} comodines", type='EVT')
        self.Msg(name, f"Has usado un comodín. Te quedan {state[name]['n_mision_joker']} comodines. Tu nueva misión es:")
        self.Msg(name, state[name]['mision'])
        card_name = GenerateCard(name)
        time.sleep(0.5)
        self.Img(name, card_name)
        time.sleep(0.5)
        return True

    def InformEveryone(self, extramsg=None):
        ''' Envia un mensaje a cada uno con su mision y su objetivo.. para hacer al inicio del juego '''
        with open(STATE, 'r') as f: state = json.load(f)
        for name in list(state.keys()):
            if extramsg is not None:
                self.Msg(name, extramsg)
            self.Msg(name, CraftMisionMsg(name)+'\n¡Suerte!')
            time.sleep(0.3)
            card_name = GenerateCard(name)
            time.sleep(0.5)
            self.Img(name, card_name)
            time.sleep(0.5)
        return True

    def CheckAndReport(self):
        ''' Comprueba el estao del juego y manda mensajes cuando solo queden 25, 10, 5 jugadores vivos, y otras alarmas '''
        with open(STATE, 'r') as f: state = json.load(f)
        live = len([name for name in state if state[name]['status']])
        if live == 25 and not self.alarm25:
            self.alarm25 = True
            self.bot.sendMsgAll(f"¡ATENCIÓN! Solo quedan 25 jugadores vivos. ¡El juego se está poniendo interesante!")
            Log(f"¡ATENCIÓN! Solo quedan 25 jugadores vivos. ¡El juego se está poniendo interesante!", type='EVT')
        elif live == 10 and not self.alarm10:
            self.alarm10 = True
            self.bot.sendMsgAll(f"¡ATENCIÓN! Solo quedan 10 jugadores vivos. Ánimo a los que hayáis llegado hasta aquí.")
            Log(f"¡ATENCIÓN! Solo quedan 10 jugadores vivos. Ánimo a los que hayáis llegado hasta aquí.", type='EVT')
        elif live == 5 and not self.alarm5:
            self.alarm5 = True
            self.bot.sendMsgAll(f"¡ATENCIÓN! Solo quedan 5 jugadores vivos. ¡Queda lo más difícil!")
            self.bot.sendMsgAll(f"¿Queréis sabes quienes quedan vivos? Podemos negociar alguna pista... o un salseo pero sólo para los que ya no están vivos ;-)")	
            Log(f"¡ATENCIÓN! Solo quedan 5 jugadores vivos. ¡Queda lo más difícil!", type='EVT')
        

###########################################
### Messages 

def CraftPersonalStatus(name):
    ''' Crea el mensaje de estado personal '''
    with open(STATE, 'r') as f:
        state = json.load(f)
    if not name in state:
        return "No estás en la lista de jugadores"
    stad = state[name]
    msg = f'¡Hola, {name}!\n'
    if stad['status']:
        msg += "Estás vivo\n"
        msg += f"Te quedan {stad['n_mision_joker']} comodines\n"
        msg += "No has usado tu habilidad\n" if stad['skill_avail'] else f"Ya has usado tu habilidad ({stad['skill']})\n"
        msg += f"Hasta ahora has completado {stad['nmisions']} misiones\n"
        msg += f"Tu misión es:\n{stad['mision']}\n"
        msg += f"Tu objetivo es:\n{stad['objetivo']}\n"
        if len(stad['list_of_kills']) > 0:
            msg += f"Hasta ahora matado a:\n{stad['list_of_kills']}\n"
    else:
        msg += "Estás muerto\n"
        msg += f"Has sido matado por {stad['killed_by']}\n"
        msg += f"Su misión era: {stad['killed_by_mision']}\n"
        msg += f"Has completado {stad['nmisions']} misiones\n"
        if len(stad['list_of_kills']) > 0:
            msg += f"Has matado a:\n{stad['list_of_kills']}\n"
    return msg

def CraftGlobalStatus():
    ''' Crea el mensaje de estado global '''
    with open(STATE, 'r') as f:
        state = json.load(f)
    nalive = 0
    ndead = 0
    bestPlayer = None
    bestScore = 0
    scores = []
    msg = "Estado del juego:\n"
    for name in state:
        if state[name]['status']:
            nalive += 1
        else:
            ndead += 1
        if state[name]['nmisions'] > bestScore:
            bestPlayer = name
            bestScore = state[name]['nmisions']
        scores.append(state[name]['nmisions'])
    msg += f"Hay {nalive} jugadores vivos y {ndead} muertos\n"
    msg += f"El mejor jugador es {bestPlayer} con {bestScore} misiones completadas\n"
    return msg
    
def CraftMisionMsg(name):
    ''' Crea el mensaje de la misión '''
    with open(STATE, 'r') as f:
        state = json.load(f)
    mision = state[name]['mision']
    objetivo = state[name]['objetivo']
    msg = f"Tu misión es:\n"
    msg += f"{mision}\n"
    msg += f"El objetivo es:\n {objetivo}\n"
    #msg += f"¡Suerte!"
    return msg

def GenerateCard(name):
    ''' Crea el mensaje y manda una imagen con él '''
    msg = CraftMisionMsg(name)
    card_name = f'mision_{name}.jpg'
    generate_card(msg, card_name)
    return card_name

def GetInstructions():
    ''' Instrucciones generales del juego, describiendo los comandos '''
    msg = '''
    ¡Esto es ScenioBOT!\n
    El juego consiste en lo siguiente:\n
    1. Cada jugador tiene una misión y un objetivo.\n
    2. Las misiones consisten, generalmente, en realizar algún tipo de interacción con otra persona del campamento. Es un juego social, así que normalmente requiere hablar con la otra persona y hacer que te cuente algo. No vayas muy a saco o sabrán a lo que vas... aprovecha la ocasión para conocer a la otra persona de verdad, pasar un rato con ella y conocerla un poco mejor.\n 
    3. Se trata de complentar el mayor número de misiones posible. Al completar una misión, matas al objetivo y heredas su misión y su objetivo.\n
    4. Cuando cumplas una misión, debes mostrar tu misión a tu objetivo (la persona que habrás matado) y tiene que estar de acuerdo con que has cumplido la misión. Si hay conflictos, contacta al master. Si estáis de acuerdo, debes declarar en el bot que has completado la misión y tu objetivo debe delcarar que está muerto. Cuando ambos lo hagáis, se te asignará una nueva misión y un nuevo objetivo.\n
    5. Si te matan rápido, no te preocupes. Puedes tener una habilidad especial que te permita seguir jugando. Todo el mundo tiene una habilidad especial pero no se sabe hasta que te maten. Normalmente tu habilidad de permite alargar el juego un poco más.\n
    6. Las habilidades especiales sólo se ejecutan mientras queden 10 personas o más vivas.\n
    7. En todo momento habrá una comunicación con el bot. Cualquier duda, contacta al máster o escribe por aquí usando las palabras clave que tienes a continuación. Es importante mirar telegram de vez en cuando para ver si hay alguna novedad... hay habilidades especiales que implican que tu objetivo pueda cambiar, ¡presta atención!\n
    8. Diviértete, pásalo bien, disfrútalo y tómate todas las misiones (las que te toquen y con las que te maten) con humor. \n
    '''
    msg2 = '''
    Palabras clave:\n
    [start] Si te has salido y has vuelto a entrar, o hubo algún reinicio, o quieres comprobar que el bot cuenta contigo.\n
    [muerto] Comando para anunciar que te han matado.\n
    [mision completada] Comando para anunciar que has completado la misión.\n
    [comodin] Comando para usar un comodín y cambiar la misión.\n
    [me retiro] Comando para retirarte del juego (si abandonas el camp antes de que el juego termine).\n
    [estado] Comando para ver tu estado actual.\n
    [mision] Comando para ver tu misión actual y tu objetivo.\n
    [master] Comando para enviar un mensaje privado al master. Tiene que empezar con la palabra \"master\", y el resto se enviará al master del juego. Para consultar dudas o lo que sea.\n
    '''
    return msg, msg2






##################################################################################################################################
##################################################################################################################################

class ScenioBot:
  
  def __init__(self, token):
    self.game = GameUpdate(self)
    self.bot = telepot.Bot(token)
    self.bot.message_loop(self.handle)
    Log('I am listening...', type='EVT')

  def setMaster(self, ID):
    #ID = GetPartID(ID)
    self.master = ID
    self.master_name = GetPartName(ID)

  def sendMaster(self, msg):
    self.bot.sendMessage(self.master, msg)
    Log(f'Message sent to master: {msg}', type='MSG')

  def sendMsg(self, ID, msg):
    ID = GetPartID(ID)
    name = GetPartName(ID)
    self.bot.sendMessage(ID, msg)
    Log(f'Message sent to {name}: {msg}', type='MSG')

  def sendImg(self, ID, imgpath):
    ID = GetPartID(ID)
    name = GetPartName(ID)
    with open(imgpath, 'rb') as f:
        self.bot.sendPhoto(ID, f)
    Log(f'Image sent to {name}: {imgpath}', type='MSG')

  def sendMsgAll(self, msg):
    with open(PART_LIST, 'r') as f:
        part_list = json.load(f)
    for ID in part_list:
        self.bot.sendMessage(ID, msg)
        time.sleep(0.3)
    Log(f'Message sent to all participants: {msg}', type='MSG')

  def handle(self, msg):
    chat_id = msg['chat']['id']
    if not 'text' in msg:
        Log(f'Got a non-text message: {msg}', type='MSG')
        Log(str(msg.keys()), type='MSG')
        return
    command_orig = msg['text']
    command =  msg['text'].lower().replace(' ', '')
    name = self.bot.getChat(chat_id)['first_name']
    Log(f'Got command: {command}', type='CMD', name=name)
    self.interpret(chat_id, command_orig, command)

  def interpret(self, chat_id, command_orig, command):
    name = self.bot.getChat(chat_id)['first_name']
    if command in ['/start', 'start']:
        alreadyInList = AddPart(chat_id, name)
        if not alreadyInList:
            Log(f'Participante {name} ya está en la lista', type='EVT')
            self.bot.sendMessage(chat_id, f'Ya estás en la lista, {name}')
        else:
            Log(f'Participante {name} añadido a la lista', type='EVT')
            self.bot.sendMessage(chat_id, f'¡Bienvenido a ScenioBOT, {name}!')
    command = command.lower().replace(' ', '').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
       
    # Comandos de juego
    ################################################################
    # Comando para anunciar que has completado la misión
    if command in ['completado', 'completada', 'misioncompletado', 'misioncompletada']:
        isok = self.game.ReportedCompleteMision(name)
        if isok:
            self.game.CheckMisionCompleted(ase=name)
            self.bot.sendMessage(chat_id, "Gracias por reportar que has completado tu misión. Recuerda que tu objetivo también tiene que reportar su muerte. Pronto tendrás noticias mías.")
            time.sleep(0.5)

    # Comando para anunciar que estás muerto
    if command in ['muerto', 'muerta', 'matado', 'matada', 'asesinado', 'asesinada', 'kill', 'killed']:
        isok = self.game.ReportedDead(name)
        if isok:
            self.game.CheckMisionCompleted(obj=name)
            self.bot.sendMessage(chat_id, "Gracias por reportar que te han matado. Recuerda que tu asesino también tiene que reportar que ha completado su misión. Proto te daré noticias.")
            time.sleep(0.5)

    # Comando para anunciar que te retiras
    if command in ['retiro', 'meretiro', 'mevoy', 'lodejo']:
        self.game.Retire(name)
        time.sleep(0.5)

    # Comando para usar un comodín	
    if command in ['comodin', 'joker', 'otramision']:
        self.game.Joker(name)
        time.sleep(0.5)

    # Comandos para mostrar información...
    ################################################################
    elif command in ['estado']:
        self.sendMsg(chat_id, CraftPersonalStatus(name))
        time.sleep(0.5)

    elif command in ['mision']:
        with open(STATE, 'r') as f:
            state = json.load(f)
        if not name in state:
            self.sendMsg(chat_id, "No estás en la lista de jugadores")
        else:
            if state[name]['status']:
                self.sendMsg(chat_id, CraftMisionMsg(name))
                card_name = GenerateCard(name)
                time.sleep(0.5)
                self.game.Img(name, card_name)
                time.sleep(0.5)
            else:
                self.sendMsg(chat_id, "Estás muerto")
        time.sleep(0.5)

    elif command.startswith('master'):
        com = [name, '-'] + command_orig.split(' ')[1:]
        com = ' '.join(com)
        self.sendMaster(com)
        time.sleep(0.5)

    # Comandos privaods
    ################################################################
    if chat_id == self.master:
        if command.startswith('pretend'):
            parts = command_orig.split(' ')
            if len(parts) < 3: return
            name = parts[1]
            chat_id = GetPartID(name)
            com = parts[2:]
            com = ' '.join(com)
            command =  com.lower().replace(' ', '')
            Log(f'Pretending commad for {name}: {com}', type='CMD', name=name)
            self.interpret(chat_id, com, command)
            time.sleep(0.5)
            # XXX

        # Comando para mostrar la lista de participantes
        elif command in ['list', 'lista', 'participantes']:
            with open(PART_LIST, 'r') as f:
                part_list = json.load(f)
            mssg = 'Lista de participantes:\n'
            for ID in part_list:
                mssg += f'{part_list[ID]} ({ID})\n'
            self.sendMaster(mssg)
            time.sleep(0.5)

        # Comando para mostrar la info de un jugador
        elif command.startswith('info'):
            name = command_orig.split(' ')[-1]
            ID = GetPartID(name)
            if ID is None:
                self.sendMaster(f'No conozco a {name}')
            else:
                self.sendMaster(CraftPersonalStatus(name))

        # Comando para mostrar el estado general del juego
        elif command in ['global', 'globalstatus', 'globalstate']:
            self.sendMaster(CraftGlobalStatus())
            time.sleep(0.5)

        # Comando para enviar notificaciones a todos los participantes
        elif command.startswith('msgall'):
            mssg = command_orig.split(' ')[1:]
            mssg = ' '.join(mssg)
            self.sendMsgAll(mssg)
            time.sleep(0.5)

        # Comando para mandar mensajes a un jugador
        elif command.startswith('msg'):
            name = command_orig.split(' ')[1]
            ID = GetPartID(name)
            if ID is None:
                self.sendMaster(f'No conozco a {name}')
            else:
                mssg = command_orig.split(' ')[2:]
                mssg = ' '.join(mssg)
                self.sendMsg(name, mssg)
                time.sleep(0.5)

        # Comando para ver un report de cada jugador
        elif command in ['report']:
            with open(STATE, 'r') as f:
                state = json.load(f)
            for name in state:
                mssg = f'{name}: \n{CraftPersonalStatus(name)}\n'
                self.sendMaster(mssg)
                time.sleep(0.2)

        # Comando para empezar el juego
        elif command in ['startgame']:
            CreateGame()
            self.sendMsgAll("¡Que empiece el juego! A continuación recibirás intrucciones básicas y, posteriormente, tu primera misión y objetivo. Asegúrate de que nadie más vea tu móvil, y no compartas esta información con nadie. ¡Suerte!")

            instructions1, instructions2 = GetInstructions()
            self.sendMsgAll(instructions1)
            time.sleep(0.5)
            self.sendMsgAll(instructions2)

            self.game.InformEveryone()
            time.sleep(0.5)

        elif command_orig.startswith('to '):
            name = command_orig.split(' ')[1]
            ID = GetPartID(name)
            if ID is None:
                self.sendMaster(f'No conozco a {name}')
            else:
                mssg = command_orig.split(' ')[2:]
                mssg = ' '.join(mssg)
                self.sendMsg(name, mssg)
                time.sleep(0.5)


if __name__ == '__main__':
    if not os.path.exists(PART_LIST):
        with open(PART_LIST, 'w') as f:
            json.dump({}, f)
    with open(TOKEN, 'r') as f:
        token = f.read().replace('\n', '')
        print('Token:', token)
    bot = ScenioBot(token)
    bot.setMaster(MASTER)
    while True:
        time.sleep(1)
