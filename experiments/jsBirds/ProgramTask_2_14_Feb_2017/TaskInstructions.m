function [  ] = TaskInstructions( window_handle, is, animal_texture, img_sizes)
% Draw task instructions and wait for key press

[Wwidth,Wheight] = WindowSize(window_handle);

DrawFormattedText(window_handle, [ ...
    'A scientist is looking for patterns in the migration of birds.\n\n' ...
    'Your job is to help him. Birds will appear one after another,\n\n' ...
    'and he wants you to take a picture\n\n' ...
    'when you spot a particular pattern in their sequence.\n\n' ...
    '(For example, a red one followed by a green one.)\n\n\n\n' ...
    '[Press any key to continue]'], 'center', 'center');
Screen('Flip', window_handle);
KbWait(); 

Y_upper = 0.5*Wheight - 0.5*0.5*img_sizes(:,2);
Y_lower = 0.5*Wheight + 0.5*0.5*img_sizes(:,2);
X_centers = 0.5*Wwidth + (-1.5:1:1.5)'*0.6*0.5.*img_sizes(:,1;
X_left = X_centers - 0.5*0.25*img_sizes(:,1);
X_right = X_centers + 0.5*0.25*img_sizes(:,1);

DrawFormattedText(window_handle, 'Here are all the birds you might see:', 'center', 0.3*Wheight);
for i_bird = 1:4
    Screen('DrawTexture', window_handle, animal_texture{i_bird}, [], [X_left(i_bird) Y_upper(i_bird) X_right(i_bird) Y_lower(i_bird)]);  % draw animal image
    DrawFormattedText(window_handle, is.animal_names{i_bird}, X_centers(i_bird), 0.7*Wheight);
end

Screen('Flip', window_handle);
KbWait([], 3); 

DrawFormattedText(window_handle, [ ...
    'We''ll always tell you what pattern to look for.\n\n' ...
    'Every few birds, there will be a new pattern to watch for.\n\n' ...
    'When you spot the pattern, press ' is.key_map{2} 'bar to take a picture!\n\n' ...
    'Unless it''s time to take a picture, you don''t need to press anything.\n\n' ...
    'The birds can appear in any order,\n\n' ...
    'including several of the same color in a row.\n\n' ...
    'A new bird will appear every two seconds or so.\n\n\n\n' ...
    '[Press any key to continue]'], 'center', 'center');
    

Screen('Flip', window_handle);
% RestrictKeysForKbCheck([])
% [~,~,keycodes]=KbCheck()
KbWait();  % wait for all keys released, then key down and release



end

