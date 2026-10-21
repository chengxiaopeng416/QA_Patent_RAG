<template>
  <div id="app">
    <transition name="page-fade" mode="out-in">
      <router-view />
    </transition>
  </div>
</template>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
  background-color: #f1f5f9;
}
</style>