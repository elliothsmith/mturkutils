function [ child ] = crossover( is, mom, dad )
% mom, dad, and child are all "trials" struct arrays

n = size(mom);

mom_inds = rand(n) < 0.5;
child(mom_inds) = mom(mom_inds);
child(~mom_inds) = dad(~mom_inds);

if rand < 0.05
    child = child(randperm(max(n)));
end

child(randi(n)).rule = randi(is.n_rules); % randomly mutate one rule
child(randi(n)).animal_identities = randperm(is.n_animals); % randomly mutate one animal_identities
temp_i = randi(n);
child(temp_i).len = randi([is.min_animals_per_trial is.max_animals_per_trial]);  % randomly mutate one animal sequence
child(temp_i).animal_sequence = randi(is.n_animals, [1 child(temp_i).len]);

end

