function [ Results ] = RunOneTrial( window_handle, dio, is, trial, fixcross, animal_texture )
% trial is a struct which is one element taken from the trials struct array in ProgramTask
% returns a struct, Results, which will become one element of a struct array in ProgramTask

animal_map = trial.animal_identities;  % the map from abstract animals to concrete animals for this trial

%% draw program for this trial
i_rule = trial.rule;
rule_text = is.rule_texts{i_rule};
for i_animal = 1:is.n_animals
    rule_text = strrep(rule_text, ['*' num2str(i_animal)], is.animal_names{animal_map(mod(i_animal-1,4)+1)+4*floor((i_animal-1)/4)}); % replace *n with singular and plural animal name strings
end
Results.rule = i_rule;
Results.animal_map = animal_map;
Results.FSM = is.FSMs{i_rule};
Results.rule_text = rule_text;

DrawFormattedText(window_handle, rule_text, 'center', 'center');
t_rule_start = Screen('Flip', window_handle);
SendTrigger(is, dio, is.RULE_TEXT_ONSET);
[t_rule_end, key_code] = KbWait([], 3);  % wait an unlimited time for a key press
key_pressed=KbName(key_code);  % translate key code into string
if strcmp(key_pressed, 'ESCAPE') % a way to bail out of PTB
    ShowCursor; sca; ListenChar(0);
    error('Escape pressed -- exiting')
end
Results.instruction_time = t_rule_end - t_rule_start;

state = 1; % start each trial in state 1
correct = 1;
n_steps = trial.len;

for i_step = 1:n_steps  % loop over the steps within a trial
    %% draw fixation cross (textures centered by default)
    Screen('DrawTexture', window_handle, fixcross);
    t_fixation = Screen('Flip', window_handle);
    SendTrigger(is, dio, is.FIXATION_ONSET);
    
    %% run the nominal FSM
    animal_input = trial.animal_sequence(i_step);  % find the abstract animal to show on this step
    new_state = is.FSMs{i_rule}(state,animal_input,1); % get the correct next state
    true_output = is.FSMs{i_rule}(state,animal_input,2); % get the correct output
    
    %% record step info into Results struct
    Results.steps(i_step).abstract_animal = animal_input;
    Results.steps(i_step).concrete_animal = is.animal_names{animal_map(animal_input)};
    Results.steps(i_step).start_state = state;
    Results.steps(i_step).end_state = new_state;
    Results.steps(i_step).true_output = is.key_map{true_output};
    
    %% draw the animal for this transition, and wait is.time_per_image, monitoring for a key press
    Screen('DrawTexture', window_handle, animal_texture{animal_map(animal_input)});  % draw animal image
    if i_step == 1
        animal_time = t_fixation + 2*is.fixation_time;  % matt thought it would be useful to have a slightly longer delay before the first animal
    else
        animal_time = t_fixation + is.fixation_time;
    end
    [~, stimulus_onset_time]=Screen('Flip', window_handle, animal_time); % flip to animal after fixation cross was on for is.fixation_time
    
    if trial.is_practice
        SendTrigger(is, dio, is.PRACTICE_ANIMAL);
    else
        trigger_code = is.ANIMAL_ONSET(i_rule, state, new_state, animal_map(animal_input), true_output);
        if isnan(trigger_code)
            disp(['i_rule=' num2str(i_rule) ', state= ' num2str(state) ', new_state= ' num2str(new_state) ', animal_map(animal_input)=' num2str(animal_map(animal_input)) ...
                ', true_output=' num2str(true_output)])
            error('bad trigger code, aborting')
        else
            SendTrigger(is, dio, trigger_code);
        end
    end
    
    [response_time, key_code] = KbWait([], 2, t_fixation + is.fixation_time + is.time_per_image);  % wait for key press
    Results.steps(i_step).RT = response_time - stimulus_onset_time;  % calculate RT
    
    key_pressed=KbName(key_code);  % translate key code into string
    Results.steps(i_step).response = '';
    if ~isempty(key_pressed)  % if the user pressed, display an outline around the animal
        disp('pressed')
        SendTrigger(is, dio, is.BUTTON_PRESS);
        Screen('DrawTexture', window_handle, animal_texture{animal_map(animal_input)});  % draw animal image
        Screen('FrameRect', window_handle, [0 0 0], ...
            CenterRectOnPointd([0 0 700 700], is.screen_center(1), is.screen_center(2)), 2)
        Screen('Flip', window_handle);
    end
    WaitSecs('UntilTime', t_fixation + is.fixation_time + is.time_per_image); % wait out the rest of the image duration
    
    %% handle the different possible keyboard events we might have seen
    if isempty(key_pressed)  % no key was pressed
        if is.single_key % FSA outputs 1 and 2 are arbitrarily mapped to mean "no-press" and "spacebar", respectively
            if true_output == 1   % correctly omitted press
                if is.subject_id == 0 || trial.is_practice % debugging output
                    DrawFormattedText(window_handle, 'Correct', 'center', 'center');
                    Screen('Flip', window_handle);
                    WaitSecs(is.debug_msg_time);
                end
                
                Results.steps(i_step).correct = 1;
            else
                if is.subject_id == 0 % debugging output
                    DrawFormattedText(window_handle, ['(debug-wrong: this is state ' num2str(state) ', with animal ' num2str(animal_input) ')'], 'center', 'center');
                    Screen('Flip', window_handle);
                    KbWait([], 2); % wait for keypress to continue
                elseif trial.is_practice
                    DrawFormattedText(window_handle, 'Oops...', 'center', 'center');
                    Screen('Flip', window_handle);
                    WaitSecs(is.debug_msg_time);
                end
                
                correct = 0;
                Results.steps(i_step).correct = 0;
            end
        else
            DrawFormattedText(window_handle, 'Time out. Please respond faster.', 'center', 'center');
            Screen('Flip', window_handle);
            WaitSecs(is.error_msg_show_time);
        end
    else  % a key was pressed
        Results.steps(i_step).response = key_pressed;
        if strcmp(key_pressed, 'ESCAPE') % a way to bail out of PTB
            ShowCursor; sca; ListenChar(0);
            error('Escape pressed -- exiting')
        elseif ~ismember(key_pressed, is.key_map)  % invalid key was pressed
            if is.single_key
                DrawFormattedText(window_handle, ['Invalid button. Please use ' is.key_map{2} '.'], 'center', 'center');
            else
                DrawFormattedText(window_handle, ['Invalid button. Please use ' is.key_map{1} ' and ' is.key_map{2} '.'], 'center', 'center');
            end
            Screen('Flip', window_handle);
            WaitSecs(is.error_msg_show_time);
            correct = 2; % code for invalid button press
            break  % abort this trial
        elseif strcmp(key_pressed,is.key_map{true_output})  % correct key was pressed
            if is.subject_id == 0 || trial.is_practice % debugging output
                DrawFormattedText(window_handle, 'Correct', 'center', 'center');
                Screen('Flip', window_handle);
                WaitSecs(is.debug_msg_time);
            end
            
            Results.steps(i_step).correct = 1;
        else
            if is.subject_id == 0 % debugging output
                DrawFormattedText(window_handle, ['(debug-wrong: this is state ' num2str(state) ', with animal ' num2str(animal_input) ')'], 'center', 'center');
                Screen('Flip', window_handle);
                KbWait([], 2); % wait for keypress to continue
            elseif trial.is_practice
                DrawFormattedText(window_handle, 'Oops...', 'center', 'center');
                Screen('Flip', window_handle);
                WaitSecs(is.debug_msg_time);
            end
            
            Results.steps(i_step).correct = 0;
            correct = 0;
        end
    end
    
    state = new_state; % update the state
end

%% draw feedback
Results.correct = correct;
if correct == 1
    if trial.is_practice
        DrawFormattedText(window_handle, 'All correct, nice job!', 'center', 'center');
    else
        DrawFormattedText(window_handle, 'Correct', 'center', 'center');
    end
    Screen('Flip', window_handle);
    SendTrigger(is, dio, is.FEEDBACK);
    WaitSecs(is.feedback_show_time);
elseif correct == 0
    if trial.is_practice
        DrawFormattedText(window_handle, 'Let''s try this one again\n\n\n[Press any key to continue]', 'center', 'center');
        Screen('Flip', window_handle);
        SendTrigger(is, dio, is.FEEDBACK);
        KbWait([], 2);
    else
        DrawFormattedText(window_handle, 'Oops...', 'center', 'center');
        Screen('Flip', window_handle);
        SendTrigger(is, dio, is.FEEDBACK);
        WaitSecs(is.feedback_show_time);
    end
end

%% fixation during ITI
Screen(window_handle, 'FillRect');
Screen('Flip', window_handle);
WaitSecs(is.ITI) % wait for ITI


end

