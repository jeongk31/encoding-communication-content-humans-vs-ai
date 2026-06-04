MASTER DATASET README
=====================

File: master_dataset.csv
Total rows: 436,938

Each row represents a single (episode x category x coder) observation with a binary label.


COLUMN DEFINITIONS
------------------

Study
    The experimental study. Values: Legitimacy, Promises, Timing.

Category
    The coding category being labeled. Values differ by study (see below).

Sender
    The participant role being coded. Only applies to the Timing study
    (values: P, V1, V2). Blank for Legitimacy and Promises.

Episode_ID
    A unique identifier for the communication episode within each study.
    Format differs by study (see below).

Coder_Type
    Whether the coder is a human research assistant or an LLM.
    Values: Human, LLM.

Encoder
    The identity of the coder.
    Human coders: H1, H2, H3.
    LLM coders: GPT, Gemini, DeepSeek.

LLM_Run
    The run number for LLM coders (1 through 5). Blank for human coders.

LLM_Version
    The prompt variant used by the LLM. Blank for human coders.
    Values:
      - Base: LLM receives the same coding instructions as human coders.
      - Ground Truth: LLM receives coding instructions plus ground truth
        examples (episodes where all human coders agreed).
      - Self Prompt: LLM generates its own coding prompt from the
        experimental and coding instructions.
      - Guidance: LLM receives coding instructions plus period context --
        all chatgroup messages from the same session-period are supplied
        together so that referential messages (e.g. "same as before") can
        be coded using the surrounding messages. (Legitimacy and Timing
        only; Promises has no Guidance variant.)

Label
    Binary coding outcome. Values: 0 or 1.


EPISODE_ID FORMAT BY STUDY
--------------------------

Legitimacy
    Format: session_period_chatGroup
    Example: 1_7_2
    Components:
      - session: Experimental session number
      - period: Game period number
      - chatGroup: Chat group identifier within the session

Promises
    Format: table_sess_id
    Example: 1_3_12
    Components:
      - table: Table number (1 or 2), distinguishing the two experimental
        pair blocks within the dataset
      - sess: Session number
      - id: Message number within the session

Timing
    Format: treatment_period_group_round_identity
    Example: 2_1_3_1_p-v1
    Components:
      - treatment: Treatment condition number
      - period: Bargaining period
      - group: Group number within the session
      - round: Negotiation round within the period
      - identity: Chat window (p-v1, p-v2, v1-v2, or public)


CATEGORIES BY STUDY
-------------------

Legitimacy (11 categories)
    Suggested effort level:
    - cat_1a_suggested_effort_0: Suggests choosing 0 hours
    - cat_1b_suggested_effort_10: Suggests choosing 10 hours
    - cat_1c_suggested_effort_20: Suggests choosing 20 hours
    - cat_1d_suggested_effort_30: Suggests choosing 30 hours
    - cat_1e_suggested_effort_40: Suggests choosing 40 hours
    - cat_1f_ambiguous_suggestion: Ambiguous suggestion - positive about
      effort but not specific about a number

    cat_2_explanation_for_effort: Provided an explanation for choosing
    suggested effort

    cat_3_trust_statements: Statements about needing to trust each other

    cat_4_positive_feedback: Positive feedback about previous outcome

    cat_5_negative_feedback: Negative feedback about previous outcome

    cat_6_social_banter: Social banter - friendly chatter not directly
    related to the game

Promises (3 categories, mutually exclusive)
    Promise (P): The message explicitly states an intention to choose
    "Roll" (i.e. to cooperate) if player A chooses "In". This includes
    direct promises, commitments, or statements of intended action.

    Empty Talk (E): The message does not express any promise or intention
    to Roll. This includes greetings, good luck wishes, jokes, general
    thoughts, comments irrelevant to the game decision, or messages
    expressing uncertainty about their intended action.

    No Message (N): No message was sent (blank or opted out). This
    category applies when Player B had the option to send a message but
    explicitly declined to do so.

Timing (4 categories, coded per sender)
    All_way_split: Whenever a member states that the total fund should be
    split between all three members, that is, that all members should get
    something. Calling for a 3-way equal split, $10 for each, is also
    coded here.

    MWC (Minimum Winning Coalition): Whenever a proposer mentions that he
    will only give money to one of the voters. When a voting member
    explicitly or implicitly tells the proposer that the other member
    should get zero.

    Compete (Competition): Whenever the proposer tells a voter the amount
    that the other voter is willing to accept, or that she is looking for
    the cheapest voter. For voters, whenever he or she asks how much the
    other one is willing to accept and seeks to undercut or match.

    Future_coalition: When non-proposers attempt to strike a deal of a
    future coalition.


SENDERS (TIMING ONLY)
---------------------

    P   Proposer
    V1  Voter 1
    V2  Voter 2

Only senders present in a given chat window are coded:
    p-v1:   P, V1
    p-v2:   P, V2
    v1-v2:  V1, V2
    public: P, V1, V2


DATA SUMMARY
-------------

                  Human    LLM (per version)   Episodes  Categories
Legitimacy        3x219    3 LLMs x 5 runs      219        11
Promises          3x91     3 LLMs x 5 runs       91         3
Timing            3x750    3 LLMs x 5 runs      750         4 (x senders)
