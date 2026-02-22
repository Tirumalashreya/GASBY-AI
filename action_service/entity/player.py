class Player:
    def __init__(self, ID, team):
        self.ID = ID
        self.team = team
        self.bboxs = {}
        self.positions = {}
        self.actions = {}
        self.previous_bb = None
        self.has_ball = False