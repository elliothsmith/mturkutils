function ProgramTask(subject_id, task_mode, recording_flag, dev_string)
%
% Last updated August 2016
% Zeb Kurth-Nelson, Matt Botvinick
% Participant observes the inputs (animals) to an FSM specified in natural
% language, and tries to match the correct output on each transition.
%
% subject_id is a unique numeric subject identifier of any length. If
%   subject_id is 0, debug messages will be shown. Mandatory argument.
% task_mode is a string which must be either 'practice', 'refresher',
%   'simple_task', or 'full_task'. Practice starts with very simple rules
%   and works up to the most complicated rules, and takes about 30 minutes.
%   Refresher takes about five minutes and is available in case patients
%   want a quick refresher right before doing the full_task experiment.
%   Simple_task is a version of the main experiment with simplified rules.
%   Full_task is the original experiment with the most complex rules.
%   Mandatory argument.
% recording_flag is a boolean flag indicating whether to attempt to send
%   triggers to the nidaq. Defaults to false. If it is false, timestamped
%   trigger values will be written to the console instead for debugging.
% dev_string should be either 'Dev1' or 'Dev2', depending on the system
%   the script is being run on.
%   

is.task_version = 2; % Version 2 adds a cover story with colored birds, a practice regime, an optional refresher, and a simplified task mode for the main experiment. 

%% Process input arguments, and set defaults for optional arguments
is.subject_id = subject_id;
is.task_mode = task_mode;
assert(strcmp(is.task_mode, 'practice') || strcmp(is.task_mode, 'refresher') || strcmp(is.task_mode, 'simple_task') || strcmp(is.task_mode, 'full_task'), ...
    'Second argument to ProgramTask should be ''practice'', ''refresher'', ''simple_task'' or ''full_task''')

if nargin <= 2
    is.recording_flag = false;
else
    is.recording_flag = recording_flag;
end

if nargin <= 3
    is.dev_string = 'Dev1';
else
    is.dev_string = dev_string;
end

%% Parameters. 'is' (InfoStruct) contains all the information about the experiment.
%% Task structure parameters
is.single_key = true; % should we use a single key (spacebar), or two keys (p and q)?
is.min_animals_per_trial = 3; % shortest trial
is.max_animals_per_trial = 6; % longest trial (uniformly sample between these inclusive endpoints)
is.n_animals = 4; % how many distinct animals in the experiment

%% Timing parameters
is.time_per_image = 2;  % how long to show each animal
is.fixation_time = 0.75; % time for fixation cross before each animal appears
is.error_msg_show_time = 1.5; % duration for displaying button press error messages within a trial
is.feedback_show_time = 1;  % duration for displaying correct/incorrect feedback at the end of a trial
is.debug_msg_time = 0.5; % time to show simple debug message
is.ITI = 2; % inter-trial interval

%% Debug timing parameters to run much faster (should normally be commented)
% is.time_per_image = 1;  % how long to show each animal
% is.fixation_time = 0.25; % time for fixation cross before each animal appears
% is.ITI = 0.5; % inter-trial interval

%% Cosmetic parameters
is.font_size = 19;
is.fullscreen = true;

%% Trigger codes (in decimal)
is.RULE_TEXT_ONSET = 100; % onset of rule text display
is.FIXATION_ONSET = 110;
if strcmp(is.task_mode, 'simple_task')
    load('trigger_codes_simple') % get the trigger_codes variables
else
    load('trigger_codes') % get the trigger_codes variables
end
is.ANIMAL_ONSET = trigger_codes;
is.PRACTICE_ANIMAL = 120;  % the code for any animal onset during a practice trial. (we don't use trigger_codes in practice trials because the semantics of the transitions are different.)
is.BUTTON_PRESS = 200;
is.FEEDBACK = 210;

%% Set up PTB
fs = filesep;
AssertOpenGL;  % check graphics
Screen('Preference', 'SkipSyncTests', 1); % Force disable sync tests (Workaround for strange synchronization failure despite apparently correctly calculating the refresh time.)

%% Set up digital triggers
if is.recording_flag
    dio = digitalio('nidaq', is.dev_string); % This instantiates the digital IO object
    hline = addline(dio, 0:7, 0, 'Out'); % This adds the 8-bit marker line to the IO object
    hline2 = addline(dio, 1, 1, 'Out'); % This adds the strobe bit line to the IO object
    putvalue(dio,[dec2binvec(0,8) 0]); % This initializes all of the bits on both lines to 0
else
    dio = [];
end

%% Set up results file
assert(strcmp(pwd, fileparts(mfilename('fullpath'))), 'Error -- Path of running .m file isn''t the same as current path') % end the program if the current path isn't the same as where this script is located.
already_loaded_randomization = false;
suffix = 0; done = false;
if ~exist('Results', 'dir'), mkdir('Results'), end % create Results folder at current path if it doesn't already exist
while ~done  % Increment suffix until filename is available
    results_file = ['Results' fs 'ProgramTask_Results_sj' num2str(is.subject_id, '%04d') '_' is.task_mode '_' num2str(suffix, '%02d') '.mat'];
    if exist(results_file,'file')
        suffix = suffix + 1;
        already_loaded_randomization = true;  % preserve the randomization for this subject id (to avoid being confusing)
        S = load(results_file, 'is');
        is.key_map = S.is.key_map;
    else
        done = true;
    end
end

%% Set up randomization, if not loaded from a pre-existing file for this subject id
if is.single_key
    is.key_map = {'', 'space'};
else
    if ~already_loaded_randomization
        is.key_map = {'q', 'p'}; is.key_map = is.key_map(randperm(2)); % randomize the response keymap between subjects.
    end
end

%% Pre-load the animal image files
is.animal_names = {'Blue', 'Green', 'Red', 'Yellow'};
animal_images = {imread(['Media' fs 'bird-blue.png']) imread(['Media' fs 'bird-green.png']) imread(['Media' fs 'bird-red.png']) imread(['Media' fs 'bird-yellow.png'])}; % 'nt' is with transparency rendered to white background

if strcmp(is.task_mode, 'simple_task')
    %% Set up the three simple FSMs. First page (:,:,1) of each cell is the new state. Second page (:,:,2) of each cell is the correct output.
    is.FSMs = cell(3,1);
    is.FSMs{1} = cat(3, [1 1 2 1; ...
                         1 1 2 1],...
                        [1 1 1 1; ...
                         1 1 2 1]); % "press for two X in a row"
    is.FSMs{2} = cat(3, [1 1 1 2; ...
                         1 1 1 2],...
                        [1 1 1 1; ...
                         2 1 1 1]); % "press for X followed by Y"
    is.FSMs{3} = cat(3, [1 2 1 1; ...
                         2 2 2 2],...
                        [2 2 1 1; ...
                         1 2 1 1]); % "press for every X until you see a Y, then press for every Y"
    is.FSMs{4} = cat(3, [2 3 4 5; ...
                         2 2 2 2; ...
                         3 3 3 3; ...
                         4 4 4 4; ...
                         5 5 5 5],...
                        [2 2 2 2; ...
                         2 1 1 1;
                         1 2 1 1;
                         1 1 2 1;
                         1 1 1 2]); % "press for two X in a row"
     
    %% There are 88 unique transition types for these FSMs. We ensure the first 33 trials contain all 88 unique types at least once.
    trials = GenerateTrialsSimple();
    is.n_trials = size(trials,2); % how many trials in the experiment
                     
    is.rule_texts{1} = ['INSTRUCTIONS:\n\n\n' ...
        'If you see a *3 bird, take a picture of the\n\n\n' ...
        'next bird if it is also *3.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    is.rule_texts{2} = ['INSTRUCTIONS:\n\n\n' ...
        'If you see a *4 bird, take a picture of the\n\n\n' ...
        'next bird if it is *1.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    is.rule_texts{3} = ['INSTRUCTIONS:\n\n\n' ...
        'Start by taking a picture of each *1 bird.\n\n\n' ...
        'But if you see a *2 bird, photograph that *2 bird,\n\n\n' ...
        'and from then on, only photograph *2 birds.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    is.rule_texts{4} = ['INSTRUCTIONS:\n\n\n' ...
        'Take a picture of the first bird you see, and then\n\n\n' ...
        'take a picture whenever you see that same bird again.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    
    is.n_rules = 4; % how many distinct rules (up to animal identity rearrangements)
elseif strcmp(is.task_mode, 'practice') || strcmp(is.task_mode, 'refresher') || strcmp(is.task_mode, 'full_task')
    %% Set up the three FSMs. First page (:,:,1) of each cell is the new state. Second page (:,:,2) of each cell is the correct output.
    is.FSMs = cell(3,1);
    is.FSMs{1} = cat(3, [1 1 1 2;       % next state from state 1 (animal 1, 2, 3, 4)
                         1 3 1 2;       % next state from state 2 (animal 1, 2, 3, 4)
                         1 1 1 2], ...  % next state from state 3 (animal 1, 2, 3, 4)
                        [1 1 1 1;       % keypress from state 1   (animal 1, 2, 3, 4)
                         1 1 1 1;       % keypress from state 2   (animal 1, 2, 3, 4)
                         1 1 2 1]);     % keypress from state 3   (animal 1, 2, 3, 4)
    is.FSMs{2} = cat(3, [3 2 3 3;       % next state from state 1 (animal 1, 2, 3, 4)
                         2 2 2 2;       % next state from state 2 (animal 1, 2, 3, 4)
                         3 3 3 3], ...  % next state from state 3 (animal 1, 2, 3, 4)
                        [1 1 1 1;       % keypress from state 1   (animal 1, 2, 3, 4)
                         1 1 2 1;       % keypress from state 2   (animal 1, 2, 3, 4)
                         1 1 1 2]);     % keypress from state 3   (animal 1, 2, 3, 4)
    is.FSMs{3} = cat(3, [2 1 1 1;       % next state from state 1 (animal 1, 2, 3, 4)
                         3 1 1 1;       % next state from state 2 (animal 1, 2, 3, 4)
                         3 3 3 3], ...  % next state from state 3 (animal 1, 2, 3, 4)
                        [1 2 1 1;       % keypress from state 1   (animal 1, 2, 3, 4)
                         1 2 1 1;       % keypress from state 2   (animal 1, 2, 3, 4)
                         1 1 2 1]);     % keypress from state 3   (animal 1, 2, 3, 4)
    
    %% There are 88 unique transition types for these FSMs. We ensure the first 33 trials contain all 88 unique types at least once.
    trials = GenerateTrials();
    is.n_trials = size(trials,2); % how many trials in the experiment
    
    %% Prepare the rule text for each rule
    is.rule_texts{1} = ['INSTRUCTIONS:\n\n\n' ...
        'Every time you see the sequence of birds:\n\n\n' ...
        '*4-*2-*3,\n\n\n'  ...
        'Photograph the third bird in that sequence.\n\n\n\n\n\n' ...
        '[Press any key to begin]'];
    is.rule_texts{2} = ['INSTRUCTIONS:\n\n\n' ...
        'If the first bird is *2, then photograph every *3 bird you see.\n\n\n' ...
        'But if the first bird is not *2, then\n\n\n' ...
        'photograph every *4 bird after the first bird.\n\n\n\n\n\n' ...
        '[Press any key to begin]'];
    is.rule_texts{3} = ['INSTRUCTIONS:\n\n\n' ...
        'Take a picture of every *2 bird, until you see at least two *1 birds in a row.\n\n\n' ...
        'Then photograph every *3 bird (but not *2 birds anymore).\n\n\n\n\n\n' ...
        '[Press any key to begin]'];

    is.n_rules = 3; % how many distinct rules (up to animal identity rearrangements)
end

try % 'try/catch' prevents getting stuck in full screen mode in case of exception
    %% Set up keyboard/mouse
    KbName('UnifyKeyNames'); % makes KbName accept same key names on all OSs
    KbCheck; % allow matlab to do some caching to improve timings later
    ListenChar(2); % disable keypresses getting to matlab. ctrl-c will re-enable.
    HideCursor;  % disable mouse cursor
    
    %% Set up display
    olddebuglevel=Screen('Preference', 'VisualDebuglevel', 3);  % reduce debug messages
    screens=Screen('Screens'); screen_number=max(screens); % will be 0 for single display setup
    if is.fullscreen
        Screen('Preference', 'ConserveVRAM', 64);  % workaround for linux opengl issue
        [window_handle,window_rect]=Screen('OpenWindow',screen_number); % default = white full screen
    else
        Screen('Preference', 'ConserveVRAM', 64);  % workaround for linux opengl issue
        [window_handle,window_rect]=Screen('OpenWindow',screen_number,[],[0 0 1024 768]); % windowed
    end
    Screen('TextSize', window_handle, is.font_size);  % set font size
    is.screen_center = nan(2,1); [is.screen_center(1), is.screen_center(2)] = RectCenter(window_rect);
    
    %% Prepare textures for drawing later
    FixCr=ones(20,20)*255; FixCr(10:11,:)=0; FixCr(:,10:11)=0;
    fixcross = Screen('MakeTexture',window_handle,FixCr);
    animal_texture = cell(4,1);
    for i_animal=1:4
        animal_texture{i_animal} = Screen('MakeTexture',window_handle,animal_images{i_animal});
    end

    %% Go through task instructions
    img_sizes = cell2mat(cellfun(@(x) size(x)', animal_images, 'UniformOutput', false))';
    TaskInstructions(window_handle, is, animal_texture, img_sizes)

    if strcmp(is.task_mode, 'practice') || strcmp(is.task_mode, 'refresher')   % RunPracticeTrials will look at the is.task_mode flag to decide which to do
        %% Run practice trials
        RunPracticeTrials(window_handle, dio, is, fixcross, animal_texture, results_file)  % this will modify Results.practice_trials
    elseif strcmp(is.task_mode, 'simple_task') || strcmp(is.task_mode, 'full_task')
        %% Do the real experiment.
        Results.datetime = datestr(now);
        for i_trial = 1:is.n_trials  % loop over trials
            Results.trials(i_trial) = RunOneTrial(window_handle, dio, is, trials(i_trial), fixcross, animal_texture);
            save(results_file, 'Results', 'is', 'trials')  % overwrite results file on every trial, in case we crash
        end % end trial loop
        
        %% Calculate and display performance feedback
        DrawFormattedText(window_handle, 'Thank you for participating!', 'center', 'center');
        Screen('Flip', window_handle);
        KbWait([], 2); %wait for keystroke
    end
    
    %% Clean up before exit
    ShowCursor; sca; ListenChar(0); Screen('Preference', 'VisualDebuglevel', olddebuglevel);
    
catch  % In case of an error in the main experiment
    ShowCursor; sca; ListenChar(0); Screen('Preference', 'VisualDebuglevel', olddebuglevel);
    psychrethrow(psychlasterror);  % can disable this if we don't want to see the red error text when we press Escape
end
