@audit @determinism @permutation
Feature: Permutation invariance for deterministic evaluation inputs
  As a governance engineer
  I want shuffled slot order to yield identical decisions
  So that ordering does not affect governance outcomes

  Scenario: Shuffled required slots produce identical outputs
    Given a deterministic evaluation with shuffled required slots
    When I run the evaluation twice with slot permutations
    Then the results should be permutation invariant
