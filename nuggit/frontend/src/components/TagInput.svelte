<script>
  import { createEventDispatcher } from 'svelte';

  // Props
  export let tags = '';

  // Internal state
  let inputValue = '';
  let inputElement;
  let tagArray = [];

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Update tagArray when tags prop changes
  // Use flags to prevent infinite reactive loops
  let lastTagsValue = '';
  let isInternalUpdate = false;

  $: if (typeof tags === 'string' && tags !== lastTagsValue && !isInternalUpdate) {
    lastTagsValue = tags;
    tagArray = tags.split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0);
  }

  // Handle input keydown events
  function handleKeydown(event) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      addTag();
    } else if (event.key === 'Backspace' && inputValue === '' && tagArray.length > 0) {
      // Remove the last tag when backspace is pressed in an empty input
      removeTag(tagArray.length - 1);
    }
  }

  // Add a new tag
  function addTag() {
    const newTag = inputValue.trim();
    if (newTag && !tagArray.includes(newTag)) {
      tagArray = [...tagArray, newTag];
      updateTags();
      inputValue = '';
    }
  }

  // Remove a tag by index
  function removeTag(index) {
    tagArray = tagArray.filter((_, i) => i !== index);
    updateTags();
    // Focus the input after removing a tag
    inputElement.focus();
  }

  // Update the tags string and dispatch change event
  function updateTags() {
    isInternalUpdate = true;
    tags = tagArray.join(',');
    lastTagsValue = tags; // Update the tracking value
    dispatch('change', { tags });
    // Reset the flag after a microtask to allow reactive statement to see the change
    setTimeout(() => {
      isInternalUpdate = false;
    }, 0);
  }

  // Handle focus on the container to focus the input
  function handleContainerClick() {
    inputElement.focus();
  }

  function handleContainerKeydown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      inputElement.focus();
    }
  }
</script>

<div
  class="tag-input-container"
  on:click={handleContainerClick}
  on:keydown={handleContainerKeydown}
  role="textbox"
  tabindex="0"
  aria-label="Tag input container"
>
  {#each tagArray as tag, index}
    <div class="tag">
      <span class="tag-text">{tag}</span>
      <button type="button" class="tag-remove" on:click={() => removeTag(index)}>×</button>
    </div>
  {/each}

  <input
    bind:this={inputElement}
    bind:value={inputValue}
    on:keydown={handleKeydown}
    on:blur={addTag}
    placeholder={tagArray.length === 0 ? "Add tags..." : ""}
    class="tag-input"
  />
</div>

<style>
  .tag-input-container {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background-color: white;
    min-height: 42px;
    cursor: text;
  }

  .tag-input-container:focus-within {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
  }

  .tag {
    display: flex;
    align-items: center;
    background-color: #dbeafe; /* Light blue background */
    color: #1e40af; /* Dark blue text for contrast */
    padding: 0.25rem 0.5rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  .tag:hover {
    background-color: #bfdbfe; /* Slightly darker blue on hover */
  }

  .tag-text {
    margin-right: 0.25rem;
  }

  .tag-remove {
    background: none;
    border: none;
    color: #1e40af; /* Dark blue to match tag color */
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    padding: 0 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s ease;
  }

  .tag-remove:hover {
    background-color: #1e40af; /* Dark blue background on hover */
    color: white;
  }

  .tag-input {
    flex: 1;
    min-width: 100px;
    border: none;
    outline: none;
    font-size: 0.95rem;
    padding: 0.25rem;
    background: transparent;
  }
</style>
