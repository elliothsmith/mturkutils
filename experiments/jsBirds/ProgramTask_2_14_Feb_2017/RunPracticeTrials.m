
function [] = RunPracticeTrials(window_handle, dio, is, fixcross, animal_texture, results_file)


if strcmp(is.task_mode, 'practice')
    DrawFormattedText(window_handle, [ ...
        'In this session we will just do practice trials.\n\n\n\n\n\n' ...
        '[Press any key to continue]'], 'center', 'center');
    Screen('Flip', window_handle);
    KbWait([], 2);
    n_pt = 1;  % count the total number of practice trials
    
    %% ONE STATE FSMs
    practice_is = is;
    
    practice_is.FSMs = cell(4,1);
    practice_is.FSMs{1} = cat(3, [1 1 1 1], [2 1 1 1]); % press for single animals
    practice_is.FSMs{2} = cat(3, [1 1 1 1], [1 2 1 1]);
    practice_is.FSMs{3} = cat(3, [1 1 1 1], [1 1 2 1]);
    practice_is.FSMs{4} = cat(3, [1 1 1 1], [1 1 1 2]);
    practice_is.rule_texts{1} = ['INSTRUCTIONS:\n\n\n' ...
        'Take a picture of any *1 bird.\n\n\n\n\n\n' ...
        '[Press any key to begin]'];
    practice_is.rule_texts{2} = ['INSTRUCTIONS:\n\n\n' ...
        'Take a picture of any *2 bird.\n\n\n\n\n\n' ...
        '[Press any key to begin]'];
    practice_is.rule_texts{3} = ['INSTRUCTIONS:\n\n\n' ...
        'Take a picture of any *3 bird.\n\n\n\n\n\n' ...
        '[Press any key to begin]'];
    practice_is.rule_texts{4} = ['INSTRUCTIONS:\n\n\n' ...
        'Take a picture of any *4 bird.\n\n\n\n\n\n' ...
        '[Press any key to begin]'];
    practice_is.n_rules = 4;
    
    % Run practice trials to press for single animal
    for i_trial = 1:4  % practice trials
        practice_trial.rule = i_trial; practice_trial.animal_identities = [1 2 3 4]; practice_trial.is_practice = true;
        practice_trial.len = 5;
        practice_trial.animal_sequence = [i_trial 1:4]; practice_trial.animal_sequence = practice_trial.animal_sequence(randperm(length(practice_trial.animal_sequence)));
        trials_completed = RunOnePracticeTrial(window_handle, dio, practice_is, practice_trial, fixcross, animal_texture); len_TC = length(trials_completed);
        Results.practice_trials(n_pt:(n_pt+len_TC-1)) = trials_completed;  % RunOnePracticeTrial can return an array of trials, if the subject doesn't get it correct the first time.
        n_pt = n_pt + len_TC;
        save(results_file, 'Results', 'is')  % write results file frequently, in case we crash
    end % end trial loop
    
    
    %% TWO STATE FSMs
    practice_is = is;
    
    practice_is.FSMs = cell(3,1);
    practice_is.FSMs{1} = cat(3, [1 1 2 1; ...
        1 1 2 1],...
        [1 1 1 1; ...
        1 1 2 1]); % "press for two X in a row"
    practice_is.FSMs{2} = cat(3, [1 1 1 2; ...
        1 1 1 2],...
        [1 1 1 1; ...
        2 1 1 1]); % "press for X followed by Y"
    practice_is.FSMs{3} = cat(3, [1 2 1 1; ...
        2 2 2 2],...
        [2 2 1 1; ...
        1 2 1 1]); % "press for every X until you see a Y, then press for every Y"
    practice_is.rule_texts{1} = ['INSTRUCTIONS:\n\n\n' ...
        'If you see a *3 bird, take a picture of the\n\n\n' ...
        'next bird if it is also *3.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    practice_is.rule_texts{2} = ['INSTRUCTIONS:\n\n\n' ...
        'If you see a *4 bird, take a picture of the\n\n\n' ...
        'next bird if it is *1.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    practice_is.rule_texts{3} = ['INSTRUCTIONS:\n\n\n' ...
        'Start by taking a picture of each *1 bird.\n\n\n' ...
        'But if you see a *2 bird, photograph that *2 bird,\n\n\n' ...
        'and from then on, only photograph *2 birds.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    practice_is.n_rules = 3;
    
    for i_type = 1:practice_is.n_rules  % iterate over different 2-state rules
        for i_bird = 1:4  % repeat each rule with four identity arrangements
            practice_trial.rule = i_type;
            practice_trial.animal_identities = [1 2 3 4]; practice_trial.animal_identities = circshift(practice_trial.animal_identities, i_bird);
            practice_trial.is_practice = true;
            if i_type==1   % define some bespoke practice sequences, designed to point out the ramifications of the rules
                if i_bird==1
                    practice_trial.animal_sequence = [2 3 3 4 2];
                elseif i_bird==2
                    practice_trial.animal_sequence = [1 3 3 3 3 1];
                elseif i_bird==3
                    practice_trial.animal_sequence = [4 2 2 2];
                elseif i_bird==4
                    practice_trial.animal_sequence = [4 4 3 1 3 3 2];
                end
            elseif i_type==2
                if i_bird==1
                    practice_trial.animal_sequence = [3 4 1 2 2];
                elseif i_bird==2
                    practice_trial.animal_sequence = [4 2 1];
                elseif i_bird==3
                    practice_trial.animal_sequence = [1 4 3 4 1 1];
                elseif i_bird==4
                    practice_trial.animal_sequence = [2 1 1 4];
                end
            elseif i_type==3
                if i_bird==1
                    practice_trial.animal_sequence = [1 1 2 2];
                elseif i_bird==2
                    practice_trial.animal_sequence = [1 3 4 4 1];
                elseif i_bird==3
                    practice_trial.animal_sequence = [2 4 3 2 1];
                elseif i_bird==4
                    practice_trial.animal_sequence = [3 1 2 1 4 2];
                end
            end
            practice_trial.len = length(practice_trial.animal_sequence);
            trials_completed = RunOnePracticeTrial(window_handle, dio, practice_is, practice_trial, fixcross, animal_texture); len_TC = length(trials_completed);
            Results.practice_trials(n_pt:(n_pt+len_TC-1)) = trials_completed;  % RunOnePracticeTrial can return an array of trials, if the subject doesn't get it correct the first time.
            n_pt = n_pt + len_TC;
            save(results_file, 'Results', 'is')  % write results file frequently, in case we crash
        end
    end % end trial loop
    
    %% SPECIAL (5-state) FSM
    practice_is = is;
    
    practice_is.FSMs = cell(1,1);
    practice_is.FSMs{1} = cat(3, [2 3 4 5; ...
        2 2 2 2; ...
        3 3 3 3; ...
        4 4 4 4; ...
        5 5 5 5],...
        [2 2 2 2; ...
        2 1 1 1;
        1 2 1 1;
        1 1 2 1;
        1 1 1 2]); % "press for two X in a row"
    practice_is.rule_texts{1} = ['INSTRUCTIONS:\n\n\n' ...
        'Take a picture of the first bird you see, and then\n\n\n' ...
        'take a picture whenever you see that same bird again.\n\n\n\n\n\n' ...
        '(Press any key to begin)'];
    practice_is.n_rules = 1;
    
    for i_bird = 1:4  % repeat each rule with four identity arrangements
        practice_trial.rule = 1;
        practice_trial.animal_identities = [1 2 3 4]; practice_trial.animal_identities = circshift(practice_trial.animal_identities, i_bird);
        practice_trial.is_practice = true;
        
        if i_bird == 1
            practice_trial.animal_sequence = [1 2 1 4];
        elseif i_bird == 2
            practice_trial.animal_sequence = [1 1 1 3];
        elseif i_bird == 3
            practice_trial.animal_sequence = [1 2 4 4];
        elseif i_bird == 4
            practice_trial.animal_sequence = [1 4 3 2 1];
        end
        
        practice_trial.len = length(practice_trial.animal_sequence);
        trials_completed = RunOnePracticeTrial(window_handle, dio, practice_is, practice_trial, fixcross, animal_texture); len_TC = length(trials_completed);
        Results.practice_trials(n_pt:(n_pt+len_TC-1)) = trials_completed;  % RunOnePracticeTrial can return an array of trials, if the subject doesn't get it correct the first time.
        n_pt = n_pt + len_TC;
        save(results_file, 'Results', 'is')  % write results file frequently, in case we crash
    end
    
    DrawFormattedText(window_handle, [ ...
        'Great work so far.\n\n' ...
        'You''re almost finished with the training.\n\n' ...
        'Now we''ll show you the three kinds of patterns\n\n' ...
        'that the scientist will be looking for in the real experiment.\n\n' ...
        'These will look a little bit more complicated,\n\n' ...
        'but you can take it slow and we''ll help as you go.\n\n\n\n\n\n' ...
        '[Press any key to continue]'], 'center', 'center');
    Screen('Flip', window_handle);
    KbWait([], 2);
    
    
    %% REAL THREE STATE FSMs
    practice_is = is;  % this gives us the FSMs and rule_texts from initialization in ProgramTask.m
    
    for i_type = 1:3  % practice trials
        for i_bird = 1:4  % repeat each rule with four identity arrangements
            practice_trial.rule = i_type;
            practice_trial.animal_identities = [1 2 3 4]; practice_trial.animal_identities = circshift(practice_trial.animal_identities, i_bird);
            practice_trial.is_practice = true;
            
            if i_type==1
                if i_bird==1
                    practice_trial.animal_sequence = [1 4 2 3 1];
                elseif i_bird==2
                    practice_trial.animal_sequence = [4 2 1 3];
                elseif i_bird==3
                    practice_trial.animal_sequence = [4 2 2 3];
                elseif i_bird==4
                    practice_trial.animal_sequence = [4 2 3 3];
                end
            elseif i_type==2
                if i_bird==1
                    practice_trial.animal_sequence = [2 3 1 1];
                elseif i_bird==2
                    practice_trial.animal_sequence = [1 4 1 1];
                elseif i_bird==3
                    practice_trial.animal_sequence = [1 2 3 4];
                elseif i_bird==4
                    practice_trial.animal_sequence = [2 4 4 2 3];
                end
            elseif i_type==3
                if i_bird==1
                    practice_trial.animal_sequence = [2 1 1 3];
                elseif i_bird==2
                    practice_trial.animal_sequence = [4 3 3];
                elseif i_bird==3
                    practice_trial.animal_sequence = [4 2 4 1 3 2];
                elseif i_bird==4
                    practice_trial.animal_sequence = [3 4 3 2];
                end
            end
            practice_trial.len = length(practice_trial.animal_sequence);
            
            trials_completed = RunOnePracticeTrial(window_handle, dio, practice_is, practice_trial, fixcross, animal_texture); len_TC = length(trials_completed);
            Results.practice_trials(n_pt:(n_pt+len_TC-1)) = trials_completed;  % RunOnePracticeTrial can return an array of trials, if the subject doesn't get it correct the first time.
            n_pt = n_pt + len_TC;
            save(results_file, 'Results', 'is')  % write results file frequently, in case we crash
        end
    end % end trial loop
    
    DrawFormattedText(window_handle, [ ...
        'Very good! That''s the end of the practice.\n\n\n\n\n\n' ...
        '(Press any key to begin)'], 'center', 'center');
    Screen('Flip', window_handle);
    KbWait();
    
elseif strcmp(is.task_mode, 'refresher')
    
    DrawFormattedText(window_handle, [ ...
        'In this session we will do a quick refresher.\n\n' ...
        'These are the patterns you''ll be asked to\n\n' ...
        'look for in the real experiment.\n\n\n\n\n\n' ...
        '[Press any key to continue]'], 'center', 'center');
    Screen('Flip', window_handle);
    KbWait([], 2);
    n_pt = 1;  % count the total number of practice/refresher trials    

    %% REAL THREE STATE FSMs
    practice_is = is;
    
    for i_type = 1:3  % practice trials
        for i_bird = 1:2  % repeat each rule with four identity arrangements
            practice_trial.rule = i_type;
            practice_trial.animal_identities = [1 2 3 4]; practice_trial.animal_identities = practice_trial.animal_identities(randperm(length(practice_trial.animal_identities)));
            practice_trial.is_practice = true;
            
            if i_type==1
                if i_bird==1
                    practice_trial.animal_sequence = [2 4 2 3 1];
                elseif i_bird==2
                    practice_trial.animal_sequence = [1 4 4 3 2];
                end
            elseif i_type==2
                if i_bird==1
                    practice_trial.animal_sequence = [2 3 1 3];
                elseif i_bird==2
                    practice_trial.animal_sequence = [4 4 1 3];
                end
            elseif i_type==3
                if i_bird==1
                    practice_trial.animal_sequence = [2 1 1 3];
                elseif i_bird==2
                    practice_trial.animal_sequence = [1 3 2 3 1];
                end
            end
            practice_trial.len = length(practice_trial.animal_sequence);
            
            trials_completed = RunOnePracticeTrial(window_handle, dio, practice_is, practice_trial, fixcross, animal_texture); len_TC = length(trials_completed);
            Results.practice_trials(n_pt:(n_pt+len_TC-1)) = trials_completed;  % RunOnePracticeTrial can return an array of trials, if the subject doesn't get it correct the first time.
            n_pt = n_pt + len_TC;
            save(results_file, 'Results', 'is')  % write results file frequently, in case we crash
        end
    end % end trial loop
    
    DrawFormattedText(window_handle, [ ...
        'Finally, we just want you to know that during\n\n' ...
        'the real experiment, you''ll only get feedback\n\n' ...
        'at the end of each block of birds.\n\n' ...
        'We''ll show you now what that feels like.\n\n' ...
        '(This is still practice).\n\n\n\n\n\n' ...
        '[Press any key to continue]'], 'center', 'center');
    Screen('Flip', window_handle);
    KbWait([], 2);
    
    for i_type = 1:3  % practice trials
        practice_trial.rule = i_type;
        practice_trial.animal_identities = [1 2 3 4]; practice_trial.animal_identities = practice_trial.animal_identities(randperm(length(practice_trial.animal_identities)));
        practice_trial.is_practice = false;   % by setting this to false, we remove the per-bird feedback
        practice_trial.animal_sequence = randi(4, [1 randi([3 6])]);
        practice_trial.len = length(practice_trial.animal_sequence);
        
        Results.practice_trials(n_pt) = RunOneTrial(window_handle, dio, practice_is, practice_trial, fixcross, animal_texture);
        n_pt = n_pt + 1;
        save(results_file, 'Results', 'is')  % write results file frequently, in case we crash
    end % end trial loop

    
    DrawFormattedText(window_handle, [ ...
        'Very good! That''s the end of the refresher.\n\n\n\n\n\n' ...
        '(Press any key to begin)'], 'center', 'center');
    Screen('Flip', window_handle);
    KbWait();
end



end





