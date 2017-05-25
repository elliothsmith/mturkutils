function [ Results ] = RunOnePracticeTrial( window_handle, dio, is, trial, fixcross, animal_texture )
% This function is a wrapper for RunOneTrial. We keep running the same trial until the subject completes it successfully.

done = false;  % if in practice mode, we will repeat this trial endlessly until it's completed correctly
repeat_index = 1;

while ~done
    
    Results(repeat_index) = RunOneTrial( window_handle, dio, is, trial, fixcross, animal_texture );
    
    if Results(repeat_index).correct == 1
        done = true;
    else
        repeat_index = repeat_index + 1;
    end
    
end

end

